"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import * as monaco from "monaco-editor";
import {
  MonacoLanguageClient,
  CloseAction,
  ErrorAction,
  MessageTransports,
} from "monaco-languageclient";
import ReconnectingWebSocket from "reconnecting-websocket";
import normalizeUrl from "normalize-url";

type File = {
  uri: string; // e.g. "file://file1.js"
  language: string; // e.g. "javascript"
  value: string;
};

type UseMonacoLspEditorProps = {
  containerRef: React.RefObject<HTMLDivElement>;
  files: File[];
  activeFileUri: string;
  onChangeFile: (uri: string, newValue: string) => void;
  onRemoveFile: (uri: string) => void;
  languageServerUrl: string; // e.g. ws://localhost:3001
  theme?: string;
};

type DiagnosticMap = Record<string, monaco.editor.IMarkerData[]>;

export function useMonacoLspEditor({
  containerRef,
  files,
  activeFileUri,
  onChangeFile,
  onRemoveFile,
  languageServerUrl,
  theme = "vs-dark",
}: UseMonacoLspEditorProps) {
  const [languageClient, setLanguageClient] =
    useState<MonacoLanguageClient | null>(null);
  const [monacoEditor, setMonacoEditor] =
    useState<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [diagnosticsMap, setDiagnosticsMap] = useState<DiagnosticMap>({});
  const [saveStatus, setSaveStatus] = useState<string>("");

  // Store view states to restore cursor/scroll on tab switch
  const viewStates = useRef<
    Record<string, monaco.editor.ICodeEditorViewState | null>
  >({});

  // Create WebSocket + language client on mount
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!containerRef.current) return;

    // Setup Monaco editor instance
    if (!monacoEditor) {
      const editor = monaco.editor.create(containerRef.current, {
        value: "",
        language: "plaintext",
        theme,
        automaticLayout: true,
      });
      setMonacoEditor(editor);
      return;
    }

    // Setup WebSocket for LSP
    const url = normalizeUrl(languageServerUrl);
    const webSocket = new ReconnectingWebSocket(url);

    function createLanguageClient(transports: MessageTransports) {
      return new MonacoLanguageClient({
        name: "Sample Language Client",
        clientOptions: {
          documentSelector: files.map((f) => ({ language: f.language })),
          errorHandler: {
            error: () => ErrorAction.Continue,
            closed: () => CloseAction.Restart,
          },
        },
        connectionProvider: {
          get: () => {
            return Promise.resolve(transports);
          },
        },
      });
    }

    webSocket.onopen = () => {
      const socket: any = webSocket;
      const reader = new WebSocketMessageReader(socket);
      const writer = new WebSocketMessageWriter(socket);
      const languageClient = createLanguageClient({ reader, writer });

      languageClient.start();
      setLanguageClient(languageClient);

      languageClient.onReady().then(() => {
        console.log("LSP Client ready");
      });

      languageClient.onNotification(
        "textDocument/publishDiagnostics",
        (params) => {
          const uri = params.uri;
          const markers: monaco.editor.IMarkerData[] = params.diagnostics.map(
            (diag: any) => ({
              severity: monaco.MarkerSeverity.Error, // map severity as needed
              startLineNumber: diag.range.start.line + 1,
              startColumn: diag.range.start.character + 1,
              endLineNumber: diag.range.end.line + 1,
              endColumn: diag.range.end.character + 1,
              message: diag.message,
              source: diag.source,
              code: diag.code,
            }),
          );

          monaco.editor.setModelMarkers(
            monaco.editor.getModel(monaco.Uri.parse(uri))!,
            "owner",
            markers,
          );

          setDiagnosticsMap((curr) => ({ ...curr, [uri]: markers }));
        },
      );
    };

    return () => {
      webSocket.close();
      languageClient?.stop();
      monacoEditor?.dispose();
    };
  }, [containerRef, files, theme]);

  // Load active file into editor and restore view state
  useEffect(() => {
    if (!monacoEditor) return;
    if (!activeFileUri) return;

    const file = files.find((f) => f.uri === activeFileUri);
    if (!file) return;

    const modelUri = monaco.Uri.parse(file.uri);
    let model = monaco.editor.getModel(modelUri);

    if (!model) {
      model = monaco.editor.createModel(file.value, file.language, modelUri);
    } else if (model.getValue() !== file.value) {
      model.setValue(file.value);
    }

    // Save previous view state
    if (monacoEditor.getModel()) {
      viewStates.current[monacoEditor.getModel()!.uri.toString()] =
        monacoEditor.saveViewState();
    }

    monacoEditor.setModel(model);
    monaco.editor.setTheme(theme);

    // Restore view state for this file if any
    const state = viewStates.current[file.uri];
    if (state) {
      monacoEditor.restoreViewState(state);
    }

    monacoEditor.focus();
  }, [activeFileUri, files, monacoEditor, theme]);

  // Handle editor content changes
  useEffect(() => {
    if (!monacoEditor) return;

    const model = monacoEditor.getModel();
    if (!model) return;

    const disposable = monacoEditor.onDidChangeModelContent(() => {
      onChangeFile(activeFileUri, model.getValue());
      setSaveStatus("Unsaved changes");
    });

    return () => disposable.dispose();
  }, [monacoEditor, activeFileUri, onChangeFile]);

  // Formatting function that sends request to LSP server
  const formatFile = useCallback(async () => {
    if (!languageClient || !monacoEditor) return;

    const model = monacoEditor.getModel();
    if (!model) return;

    const params = {
      textDocument: {
        uri: model.uri.toString(),
      },
      options: {
        tabSize: monacoEditor.getOption(monaco.editor.EditorOption.tabSize),
        insertSpaces: monacoEditor.getOption(
          monaco.editor.EditorOption.insertSpaces,
        ),
      },
    };

    try {
      const edits = await languageClient.sendRequest(
        "textDocument/formatting",
        params,
      );

      if (Array.isArray(edits)) {
        const monacoEdits = edits.map((edit: any) => ({
          range: new monaco.Range(
            edit.range.start.line + 1,
            edit.range.start.character + 1,
            edit.range.end.line + 1,
            edit.range.end.character + 1,
          ),
          text: edit.newText,
        }));

        model.pushEditOperations([], monacoEdits, () => null);
      }
    } catch (err) {
      console.error("LSP formatting failed", err);
    }
  }, [languageClient, monacoEditor]);

  // Remove current file handler
  const removeFile = useCallback(() => {
    onRemoveFile(activeFileUri);
  }, [activeFileUri, onRemoveFile]);

  // Autosave simulation (extend this to call your backend API)
  useEffect(() => {
    if (!monacoEditor) return;
    if (saveStatus !== "Unsaved changes") return;

    const timeout = setTimeout(() => {
      // Example: call your backend save API here
      setSaveStatus("Saved");
    }, 1000);

    return () => clearTimeout(timeout);
  }, [saveStatus, monacoEditor]);

  return {
    diagnosticsMap,
    saveStatus,
    formatFile,
    removeFile,
  };
}
