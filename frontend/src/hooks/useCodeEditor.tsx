import { useState, useEffect } from "react";
import * as monaco from "monaco-editor";

export function useCodeEditor() {
  const [editor, setEditor] =
    useState<monaco.editor.IStandaloneCodeEditor | null>(null);

  useEffect(() => {
    // Required cleanup on component unmount
    return () => {
      if (editor) {
        editor.dispose();
      }
    };
  }, [editor]);

  const createEditor = (
    container: HTMLElement,
    value: string = "",
    language: string = "javascript",
  ) => {
    // Set up the editor
    const editorInstance = monaco.editor.create(container, {
      value,
      language,
      theme: "vs-dark",
      automaticLayout: true,
      minimap: {
        enabled: true,
        scale: 0.8,
      },
      scrollBeyondLastLine: false,
      fontSize: 14,
      fontFamily: "'Fira Code', Menlo, Monaco, 'Courier New', monospace",
      fontLigatures: true,
      tabSize: 2,
      lineNumbers: "on",
      glyphMargin: true,
      folding: true,
      renderLineHighlight: "all",
      scrollbar: {
        useShadows: false,
        verticalScrollbarSize: 10,
        horizontalScrollbarSize: 10,
        verticalHasArrows: false,
        horizontalHasArrows: false,
        alwaysConsumeMouseWheel: false,
      },
      overviewRulerBorder: false,
      renderIndentGuides: true,
      contextmenu: true,
      quickSuggestions: true,
      acceptSuggestionOnCommitCharacter: true,
      acceptSuggestionOnEnter: "on",
      wordWrap: "on",
      wordWrapColumn: 80,
    });

    setEditor(editorInstance);
    return editorInstance;
  };

  return {
    editor,
    createEditor,
  };
}
