import React, { useEffect, useRef } from "react";
import * as monaco from "monaco-editor";
import {
  createMessageConnection,
  WebSocketMessageReader,
  WebSocketMessageWriter,
  NotificationType,
} from "vscode-ws-jsonrpc";

type MonacoEditorProps = {
  value: string;
  language: string;
  onChange?: (value: string) => void;
  websocketUrl?: string; // WebSocket server URL for JSON-RPC
};

const MonacoEditor: React.FC<MonacoEditorProps> = ({
  value,
  language,
  onChange,
  websocketUrl,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const connectionRef = useRef<any>(null);
  const webSocketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (containerRef.current) {
      editorRef.current = monaco.editor.create(containerRef.current, {
        value,
        language,
        automaticLayout: true,
      });

      editorRef.current.onDidChangeModelContent(() => {
        if (onChange && editorRef.current) {
          const val = editorRef.current.getValue();
          onChange(val);
        }
      });
    }

    return () => {
      editorRef.current?.dispose();
    };
  }, [language]);

  useEffect(() => {
    if (editorRef.current && editorRef.current.getValue() !== value) {
      editorRef.current.setValue(value);
    }
  }, [value]);

  // Setup JSON-RPC connection over WebSocket if websocketUrl is provided
  useEffect(() => {
    if (!websocketUrl) return;

    webSocketRef.current = new WebSocket(websocketUrl);

    const socket = webSocketRef.current;

    socket.onopen = () => {
      connectionRef.current = createMessageConnection(
        new WebSocketMessageReader(socket),
        new WebSocketMessageWriter(socket)
      );

      connectionRef.current.listen();

      // Example notification type for demo
      const notification = new NotificationType<{ message: string }>(
        "exampleNotification"
      );

      // Send a notification to the server
      connectionRef.current.sendNotification(notification, {
        message: "Hello from MonacoEditor!",
      });

      // Listen for notifications from server
      connectionRef.current.onNotification(notification, (params) => {
        console.log("Received notification:", params.message);
      });
    };

    socket.onclose = () => {
      connectionRef.current?.dispose();
      connectionRef.current = null;
      webSocketRef.current = null;
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    return () => {
      connectionRef.current?.dispose();
      webSocketRef.current?.close();
    };
  }, [websocketUrl]);

  return <div ref={containerRef} style={{ width: "100%", height: "500px" }} />;
};

export default MonacoEditor;
