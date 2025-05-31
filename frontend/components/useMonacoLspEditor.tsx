 Update useMonacoLspEditor.ts to Trigger LSP Rename
Update your existing renameFile() to send an LSP workspace/applyRenameFile notification:

ts
Copy
Edit
const renameFile = useCallback(
  async (oldUri: string, newUri: string) => {
    const oldModel = monaco.editor.getModel(monaco.Uri.parse(oldUri));
    if (!oldModel || !languageClient) return;

    const newModel = monaco.editor.createModel(
      oldModel.getValue(),
      oldModel.getLanguageId(),
      monaco.Uri.parse(newUri)
    );
    oldModel.dispose();
    monacoEditor?.setModel(newModel);

    try {
      await languageClient.sendRequest("workspace/willRenameFiles", {
        files: [{ oldUri, newUri }],
      });
    } catch (err) {
      console.error("LSP rename failed", err);
    }
  },
  [languageClient, monacoEditor]
); "use client";
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
import {
  WebSocketMessageReader,
  WebSocketMessageWriter,
} from "vscode-ws-jsonrpc";

type File = {
  uri: string;
  language: string;
  value: string;
};

type UseMonacoLspEditorProps = {
  containerRef: React.RefObject<HTMLDivElement>;
  files: File[];
  activeFileUri: string;
  onChangeFile: (uri: string, newValue: string) => void;
  onRemoveFile: (uri: string) => void;
  languageServerUrl: string;
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
  const [languageClient, setLanguageClient] = useState<MonacoLanguageClient | null>(null);
  const [monacoEditor, setMonacoEditor] = useState<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [diagnosticsMap, setDiagnosticsMap] = useState<DiagnosticMap>({});
  const [saveStatus, setSaveStatus] = useState<string>("");

  const viewStates = useRef<Record<string, monaco.editor.ICodeEditorViewState | null>>({});

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!containerRef.current) return;

    if (!monacoEditor) {
      const editor = monaco.editor.create(containerRef.current, {
        value: "",
        language: "plaintext",
        theme,
        automaticLayout: true,
      });

      // Save shortcut
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        setSaveStatus("Saved");
      });

      setMonacoEditor(editor);
      return;
    }

    const url = normalizeUrl(languageServerUrl);
    const webSocket = new ReconnectingWebSocket(url);

    function createLanguageClient(transports: MessageTransports) {
      return new MonacoLanguageClient({
        name: "LSP Client",
        clientOptions: {
          documentSelector: files.map((f) => ({ language: f.language })),
          synchronize: {
            configurationSection: ["*"],
          },
          errorHandler: {
            error: () => ErrorAction.Continue,
            closed: () => CloseAction.Restart,
          },
        },
        connectionProvider: {
          get: () => Promise.resolve(transports),
        },
      });
    }

    webSocket.onopen = () => {
      const socket: any = webSocket;
      const reader = new WebSocketMessageReader(socket);
      const writer = new WebSocketMessageWriter(socket);
      const client = createLanguageClient({ reader, writer });

      client.start();
      setLanguageClient(client);

      client.onReady().then(() => {
        console.log("LSP Client ready");
      });

      client.onNotification("textDocument/publishDiagnostics", (params) => {
        const uri = params.uri;
        const markers: monaco.editor.IMarkerData[] = params.diagnostics.map((diag: any) => ({
          severity:
            diag.severity === 1
              ? monaco.MarkerSeverity.Error
              : diag.severity === 2
              ? monaco.MarkerSeverity.Warning
              : monaco.MarkerSeverity.Info,
          startLineNumber: diag.range.start.line + 1,
          startColumn: diag.range.start.character + 1,
          endLineNumber: diag.range.end.line + 1,
          endColumn: diag.range.end.character + 1,
          message: diag.message,
          source: diag.source,
          code: diag.code,
        }));

        const model = monaco.editor.getModel(monaco.Uri.parse(uri));
        if (model) {
          monaco.editor.setModelMarkers(model, "owner", markers);
        }

        setDiagnosticsMap((curr) => ({ ...curr, [uri]: markers }));
      });
    };

    return () => {
      webSocket.close();
      languageClient?.stop();
      monacoEditor?.dispose();
    };
  }, [containerRef, files, languageServerUrl, theme, monacoEditor]);

  useEffect(() => {
    if (!monacoEditor || !activeFileUri) return;

    const file = files.find((f) => f.uri === activeFileUri);
    if (!file) return;

    const uri = monaco.Uri.parse(file.uri);
    let model = monaco.editor.getModel(uri);

    if (!model) {
      model = monaco.editor.createModel(file.value, file.language, uri);
    } else if (model.getValue() !== file.value) {
      model.setValue(file.value);
    }

    if (monacoEditor.getModel()) {
      viewStates.current[monacoEditor.getModel()!.uri.toString()] = monacoEditor.saveViewState();
    }

    monacoEditor.setModel(model);
    monaco.editor.setTheme(theme);

    const viewState = viewStates.current[file.uri];
    if (viewState) monacoEditor.restoreViewState(viewState);
    monacoEditor.focus();
  }, [activeFileUri, files, monacoEditor, theme]);

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

  const formatFile = useCallback(async () => {
    if (!languageClient || !monacoEditor) return;
    const model = monacoEditor.getModel();
    if (!model) return;

    const params = {
      textDocument: { uri: model.uri.toString() },
      options: {
        tabSize: monacoEditor.getOption(monaco.editor.EditorOption.tabSize),
        insertSpaces: monacoEditor.getOption(monaco.editor.EditorOption.insertSpaces),
      },
    };

    try {
      const edits = await languageClient.sendRequest("textDocument/formatting", params);
      if (Array.isArray(edits)) {
        const monacoEdits = edits.map((edit: any) => ({
          range: new monaco.Range(
            edit.range.start.line + 1,
            edit.range.start.character + 1,
            edit.range.end.line + 1,
            edit.range.end.character + 1
          ),
          text: edit.newText,
        }));
        model.pushEditOperations([], monacoEdits, () => null);
      }
    } catch (err) {
      console.error("LSP formatting failed", err);
    }
  }, [languageClient, monacoEditor]);

  const removeFile = useCallback(() => {
    onRemoveFile(activeFileUri);
  }, [activeFileUri, onRemoveFile]);

  // Simulate autosave
  useEffect(() => {
    if (!monacoEditor || saveStatus !== "Unsaved changes") return;

    const timeout = setTimeout(() => {
      setSaveStatus("Saved");
    }, 1000);

    return () => clearTimeout(timeout);
  }, [saveStatus, monacoEditor]);

  const renameFile = useCallback(
    async (oldUri: string, newUri: string) => {
      const oldModel = monaco.editor.getModel(monaco.Uri.parse(oldUri));
      if (!oldModel) return;

      // Inform LSP server
      if (languageClient) {
        await languageClient.sendNotification("workspace/didRenameFiles", {
          files: [{ oldUri, newUri }],
        });
      }

      // Replace model
      const newModel = monaco.editor.createModel(
        oldModel.getValue(),
        oldModel.getLanguageId(),
        monaco.Uri.parse(newUri)
      );
      oldModel.dispose();
      monacoEditor?.setModel(newModel);
    },
    [languageClient, monacoEditor]
  );

  const showDiff = useCallback(
    (uri1: string, uri2: string) => {
      const model1 = monaco.editor.getModel(monaco.Uri.parse(uri1));
      const model2 = monaco.editor.getModel(monaco.Uri.parse(uri2));

      if (model1 && model2 && containerRef.current) {
        monaco.editor.createDiffEditor(containerRef.current, {
          theme,
          automaticLayout: true,
        }).setModel({ original: model1, modified: model2 });
      }
    },
    [containerRef, theme]
  );

  return {
    diagnosticsMap,
    saveStatus,
    formatFile,
    removeFile,
    renameFile,
    showDiff,
  };
}

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
import {
  WebSocketMessageReader,
  WebSocketMessageWriter,
} from "vscode-ws-jsonrpc";

type File = {
  uri: string;
  language: string;
  value: string;
};

type UseMonacoLspEditorProps = {
  containerRef: React.RefObject<HTMLDivElement>;
  files: File[];
  activeFileUri: string;
  onChangeFile: (uri: string, newValue: string) => void;
  onRemoveFile: (uri: string) => void;
  languageServerUrl: string;
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
  const [languageClient, setLanguageClient] = useState<MonacoLanguageClient | null>(null);
  const [monacoEditor, setMonacoEditor] = useState<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [diagnosticsMap, setDiagnosticsMap] = useState<DiagnosticMap>({});
  const [saveStatus, setSaveStatus] = useState<string>("");

  const viewStates = useRef<Record<string, monaco.editor.ICodeEditorViewState | null>>({});

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!containerRef.current) return;

    if (!monacoEditor) {
      const editor = monaco.editor.create(containerRef.current, {
        value: "",
        language: "plaintext",
        theme,
        automaticLayout: true,
      });

      // Save shortcut
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        setSaveStatus("Saved");
      });

      setMonacoEditor(editor);
      return;
    }

    const url = normalizeUrl(languageServerUrl);
    const webSocket = new ReconnectingWebSocket(url);

    function createLanguageClient(transports: MessageTransports) {
      return new MonacoLanguageClient({
        name: "LSP Client",
        clientOptions: {
          documentSelector: files.map((f) => ({ language: f.language })),
          synchronize: {
            configurationSection: ["*"],
          },
          errorHandler: {
            error: () => ErrorAction.Continue,
            closed: () => CloseAction.Restart,
          },
        },
        connectionProvider: {
          get: () => Promise.resolve(transports),
        },
      });
    }

    webSocket.onopen = () => {
      const socket: any = webSocket;
      const reader = new WebSocketMessageReader(socket);
      const writer = new WebSocketMessageWriter(socket);
      const client = createLanguageClient({ reader, writer });

      client.start();
      setLanguageClient(client);

      client.onReady().then(() => {
        console.log("LSP Client ready");
      });

      client.onNotification("textDocument/publishDiagnostics", (params) => {
        const uri = params.uri;
        const markers: monaco.editor.IMarkerData[] = params.diagnostics.map((diag: any) => ({
          severity:
            diag.severity === 1
              ? monaco.MarkerSeverity.Error
              : diag.severity === 2
              ? monaco.MarkerSeverity.Warning
              : monaco.MarkerSeverity.Info,
          startLineNumber: diag.range.start.line + 1,
          startColumn: diag.range.start.character + 1,
          endLineNumber: diag.range.end.line + 1,
          endColumn: diag.range.end.character + 1,
          message: diag.message,
          source: diag.source,
          code: diag.code,
        }));

        const model = monaco.editor.getModel(monaco.Uri.parse(uri));
        if (model) {
          monaco.editor.setModelMarkers(model, "owner", markers);
        }

        setDiagnosticsMap((curr) => ({ ...curr, [uri]: markers }));
      });
    };

    return () => {
      webSocket.close();
      languageClient?.stop();
      monacoEditor?.dispose();
    };
  }, [containerRef, files, languageServerUrl, theme, monacoEditor]);

  useEffect(() => {
    if (!monacoEditor || !activeFileUri) return;

    const file = files.find((f) => f.uri === activeFileUri);
    if (!file) return;

    const uri = monaco.Uri.parse(file.uri);
    let model = monaco.editor.getModel(uri);

    if (!model) {
      model = monaco.editor.createModel(file.value, file.language, uri);
    } else if (model.getValue() !== file.value) {
      model.setValue(file.value);
    }

    if (monacoEditor.getModel()) {
      viewStates.current[monacoEditor.getModel()!.uri.toString()] = monacoEditor.saveViewState();
    }

    monacoEditor.setModel(model);
    monaco.editor.setTheme(theme);

    const viewState = viewStates.current[file.uri];
    if (viewState) monacoEditor.restoreViewState(viewState);
    monacoEditor.focus();
  }, [activeFileUri, files, monacoEditor, theme]);

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

  const formatFile = useCallback(async () => {
    if (!languageClient || !monacoEditor) return;
    const model = monacoEditor.getModel();
    if (!model) return;

    const params = {
      textDocument: { uri: model.uri.toString() },
      options: {
        tabSize: monacoEditor.getOption(monaco.editor.EditorOption.tabSize),
        insertSpaces: monacoEditor.getOption(monaco.editor.EditorOption.insertSpaces),
      },
    };

    try {
      const edits = await languageClient.sendRequest("textDocument/formatting", params);
      if (Array.isArray(edits)) {
        const monacoEdits = edits.map((edit: any) => ({
          range: new monaco.Range(
            edit.range.start.line + 1,
            edit.range.start.character + 1,
            edit.range.end.line + 1,
            edit.range.end.character + 1
          ),
          text: edit.newText,
        }));
        model.pushEditOperations([], monacoEdits, () => null);
      }
    } catch (err) {
      console.error("LSP formatting failed", err);
    }
  }, [languageClient, monacoEditor]);

  const removeFile = useCallback(() => {
    onRemoveFile(activeFileUri);
  }, [activeFileUri, onRemoveFile]);

  // Simulate autosave
  useEffect(() => {
    if (!monacoEditor || saveStatus !== "Unsaved changes") return;

    const timeout = setTimeout(() => {
      setSaveStatus("Saved");
    }, 1000);

    return () => clearTimeout(timeout);
  }, [saveStatus, monacoEditor]);

  const renameFile = useCallback(
    async (oldUri: string, newUri: string) => {
      const oldModel = monaco.editor.getModel(monaco.Uri.parse(oldUri));
      if (!oldModel) return;

      // Inform LSP server
      if (languageClient) {
        await languageClient.sendNotification("workspace/didRenameFiles", {
          files: [{ oldUri, newUri }],
        });
      }

      // Replace model
      const newModel = monaco.editor.createModel(
        oldModel.getValue(),
        oldModel.getLanguageId(),
        monaco.Uri.parse(newUri)
      );
      oldModel.dispose();
      monacoEditor?.setModel(newModel);
    },
    [languageClient, monacoEditor]
  );

  const showDiff = useCallback(
    (uri1: string, uri2: string) => {
      const model1 = monaco.editor.getModel(monaco.Uri.parse(uri1));
      const model2 = monaco.editor.getModel(monaco.Uri.parse(uri2));

      if (model1 && model2 && containerRef.current) {
        monaco.editor.createDiffEditor(containerRef.current, {
          theme,
          automaticLayout: true,
        }).setModel({ original: model1, modified: model2 });
      }
    },
    [containerRef, theme]
  );

  return {
    diagnosticsMap,
    saveStatus,
    formatFile,
    removeFile,
    renameFile,
    showDiff,
  };
}
