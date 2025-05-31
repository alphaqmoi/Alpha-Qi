import * as monaco from "monaco-editor";
import {
  MonacoLanguageClient,
  CloseAction,
  ErrorAction,
  MonacoServices,
  createConnection,
} from "monaco-languageclient";
import normalizeUrl from "normalize-url";
import ReconnectingWebSocket from "reconnecting-websocket";
import {
  useEffect,
  useRef,
  useState,
  useCallback,
  MutableRefObject,
} from "react";

interface UseMonacoLspEditorProps {
  editorRef: MutableRefObject<monaco.editor.IStandaloneCodeEditor | null>;
  languageId: string;
  fileUri: string;
}

export const useMonacoLspEditor = ({
  editorRef,
  languageId,
  fileUri,
}: UseMonacoLspEditorProps) => {
  const [languageClient, setLanguageClient] =
    useState<MonacoLanguageClient | null>(null);
  const editorInstanceRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(
    null,
  );

  const createLanguageClient = (webSocket: WebSocket): MonacoLanguageClient => {
    const connection = createConnection(webSocket as any);

    return new MonacoLanguageClient({
      name: "Monaco Language Client",
      clientOptions: {
        documentSelector: [{ language: languageId }],
        errorHandler: {
          error: () => ErrorAction.Continue,
          closed: () => CloseAction.Restart,
        },
      },
      connectionProvider: {
        get: () => Promise.resolve(connection),
      },
    });
  };

  useEffect(() => {
    if (!editorRef.current) return;

    MonacoServices.install(editorRef.current);

    const url = normalizeUrl(`ws://localhost:3000/lsp/${languageId}`);
    const webSocket = new ReconnectingWebSocket(url);

    webSocket.onopen = () => {
      const client = createLanguageClient(webSocket as WebSocket);
      client.start();
      setLanguageClient(client);
    };

    editorInstanceRef.current = editorRef.current;

    return () => {
      if (languageClient) {
        languageClient.stop();
      }
    };
  }, [editorRef, languageId]);

  const renameFile = useCallback(
    async (oldUri: string, newUri: string) => {
      const oldModel = monaco.editor.getModel(monaco.Uri.parse(oldUri));
      if (!oldModel || !languageClient) return;

      try {
        // Send willRenameFiles request before the rename
        await languageClient.sendRequest("workspace/willRenameFiles", {
          files: [{ oldUri, newUri }],
        });
      } catch (err) {
        console.warn("LSP 'willRenameFiles' failed (continuing anyway)", err);
      }

      // Perform rename operation
      const newModel = monaco.editor.createModel(
        oldModel.getValue(),
        oldModel.getLanguageId(),
        monaco.Uri.parse(newUri),
      );

      oldModel.dispose();
      editorInstanceRef.current?.setModel(newModel);

      try {
        // Send didRenameFiles notification after the rename
        await languageClient.sendNotification("workspace/didRenameFiles", {
          files: [{ oldUri, newUri }],
        });
      } catch (err) {
        console.warn("LSP 'didRenameFiles' notification failed", err);
      }
    },
    [languageClient],
  );

  return {
    renameFile,
    languageClient,
  };
};
