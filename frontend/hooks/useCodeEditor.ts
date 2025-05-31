"use client";

import { useEffect, useRef, useCallback } from "react";
import * as monaco from "monaco-editor";

type UseCodeEditorParams = {
  containerRef: React.RefObject<HTMLDivElement>;
  value: string;
  language?: string;
  onChange?: (value: string) => void;
  onAutoSave?: (value: string) => Promise<void> | void;
  autoSaveDebounceMs?: number;
  tabSize?: number;
  insertSpaces?: boolean;
  theme?: string;
};

export function useCodeEditor({
  containerRef,
  value,
  language = "javascript",
  onChange,
  onAutoSave,
  autoSaveDebounceMs = 1500,
  tabSize = 2,
  insertSpaces = true,
  theme = "vs-dark",
}: UseCodeEditorParams) {
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const changeListenerRef = useRef<monaco.IDisposable | null>(null);
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Create editor instance once containerRef is set and editor not created
  useEffect(() => {
    if (!containerRef.current || editorRef.current) return;

    const editor = monaco.editor.create(containerRef.current, {
      value,
      language,
      theme,
      automaticLayout: true,
      minimap: { enabled: false },
      tabSize,
      insertSpaces,
    });

    editorRef.current = editor;

    return () => {
      changeListenerRef.current?.dispose();
      editor.dispose();
      editorRef.current = null;
      if (autoSaveTimeoutRef.current) clearTimeout(autoSaveTimeoutRef.current);
    };
  }, [containerRef]);

  // Sync external value, language, and options into editor
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    const model = editor.getModel();
    if (!model) return;

    // Update value if changed externally
    if (model.getValue() !== value) {
      model.setValue(value);
    }

    // Update language if changed externally
    if (model.getLanguageId() !== language) {
      monaco.editor.setModelLanguage(model, language);
    }

    editor.updateOptions({
      tabSize,
      insertSpaces,
      theme,
    });
  }, [value, language, tabSize, insertSpaces, theme]);

  // Listen for content changes, trigger onChange and debounced autosave
  useEffect(() => {
    if (!editorRef.current) return;

    // Dispose previous listener if any
    changeListenerRef.current?.dispose();

    if (onChange || onAutoSave) {
      const model = editorRef.current.getModel();
      if (!model) return;

      changeListenerRef.current = model.onDidChangeContent(() => {
        const updatedValue = model.getValue();

        if (onChange) onChange(updatedValue);

        if (onAutoSave) {
          if (autoSaveTimeoutRef.current)
            clearTimeout(autoSaveTimeoutRef.current);
          autoSaveTimeoutRef.current = setTimeout(() => {
            onAutoSave(updatedValue);
          }, autoSaveDebounceMs);
        }
      });
    }

    return () => {
      changeListenerRef.current?.dispose();
      changeListenerRef.current = null;
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
        autoSaveTimeoutRef.current = null;
      }
    };
  }, [onChange, onAutoSave, autoSaveDebounceMs]);

  // Manual editor creation for dynamic swapping or re-creating editor
  const createEditor = useCallback(
    (
      container: HTMLDivElement,
      initialValue: string,
      language: string,
    ): monaco.editor.IStandaloneCodeEditor => {
      if (editorRef.current) {
        changeListenerRef.current?.dispose();
        editorRef.current.dispose();
        editorRef.current = null;
      }

      const editor = monaco.editor.create(container, {
        value: initialValue,
        language,
        theme,
        automaticLayout: true,
        minimap: { enabled: false },
        tabSize,
        insertSpaces,
      });

      editorRef.current = editor;
      return editor;
    },
    [theme, tabSize, insertSpaces],
  );

  // Utility functions
  const getValue = () => editorRef.current?.getValue() ?? "";
  const setValue = (newValue: string) => {
    const model = editorRef.current?.getModel();
    if (model && model.getValue() !== newValue) {
      model.setValue(newValue);
    }
  };

  const undo = () => editorRef.current?.trigger("keyboard", "undo", null);
  const redo = () => editorRef.current?.trigger("keyboard", "redo", null);
  const search = () =>
    editorRef.current?.trigger("keyboard", "actions.find", null);
  const replace = () =>
    editorRef.current?.trigger(
      "keyboard",
      "editor.action.startFindReplaceAction",
      null,
    );

  const saveViewState = () => editorRef.current?.saveViewState() ?? null;
  const restoreViewState = (state: any) =>
    editorRef.current?.restoreViewState(state);

  return {
    editor: editorRef.current,
    getValue,
    setValue,
    createEditor,
    undo,
    redo,
    search,
    replace,
    saveViewState,
    restoreViewState,
  };
}
