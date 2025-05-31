"use client";

import { useEffect, useRef } from "react";
import * as monaco from "monaco-editor";

type UseCodeEditorParams = {
  containerRef: React.RefObject<HTMLDivElement>;
  value: string;
  language?: string;
  onChange?: (value: string) => void;
  theme?: string;
};

export function useCodeEditor({
  containerRef,
  value,
  language = "javascript",
  onChange,
  theme = "vs-dark",
}: UseCodeEditorParams) {
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);

  useEffect(() => {
    if (!containerRef.current || editorRef.current) return;

    // Create the Monaco editor instance
    const editor = monaco.editor.create(containerRef.current, {
      value,
      language,
      theme,
      automaticLayout: true,
      minimap: { enabled: false },
    });

    editorRef.current = editor;

    const model = editor.getModel();

    // Register change listener to update external state
    const changeListener = model?.onDidChangeContent(() => {
      onChange?.(model.getValue());
    });

    return () => {
      changeListener?.dispose();
      editor.dispose();
      editorRef.current = null;
    };
  }, [containerRef, language, theme]);

  // Keep editor content in sync with external `value` changes
  useEffect(() => {
    if (!editorRef.current) return;
    const model = editorRef.current.getModel();
    if (model && model.getValue() !== value) {
      model.setValue(value);
    }
  }, [value]);

  return {
    editor: editorRef.current,
  };
}
