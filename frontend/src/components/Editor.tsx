import { useEffect, useRef } from "react";
import * as monaco from "monaco-editor";
import { FileType } from "@/hooks/useFiles";
import { useCodeEditor } from "@/hooks/useCodeEditor";

type EditorProps = {
  file: FileType;
  onChange: (content: string) => void;
};

const Editor = ({ file, onChange }: EditorProps) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const { editor, createEditor } = useCodeEditor();

  useEffect(() => {
    if (editorRef.current && !editor) {
      const newEditor = createEditor(
        editorRef.current,
        file.content || "",
        getLanguage(file.name),
      );

      newEditor.onDidChangeModelContent(() => {
        onChange(newEditor.getValue());
      });
    }

    return () => {
      if (editor) {
        editor.dispose();
      }
    };
  }, []);

  useEffect(() => {
    if (editor) {
      const model = editor.getModel();
      if (model) {
        monaco.editor.setModelLanguage(model, getLanguage(file.name));
      }
      editor.setValue(file.content || "");
    }
  }, [file.id, file.content, editor]);

  const getLanguage = (filename: string): string => {
    const extension = filename.split(".").pop()?.toLowerCase();

    switch (extension) {
      case "js":
        return "javascript";
      case "jsx":
        return "javascript";
      case "ts":
        return "typescript";
      case "tsx":
        return "typescript";
      case "py":
        return "python";
      case "html":
        return "html";
      case "css":
        return "css";
      case "json":
        return "json";
      case "md":
        return "markdown";
      case "env":
        return "plaintext";
      default:
        return "plaintext";
    }
  };

  return (
    <>
      <div className="flex text-sm py-1 px-4 bg-darker border-b border-gray-800">
        <button className="px-3 py-1 text-xs rounded hover:bg-gray-800">
          <i className="ri-save-line mr-1"></i> Save
        </button>
        <div className="ml-auto text-xs text-gray-500 flex items-center">
          <span>
            {getLanguage(file.name).charAt(0).toUpperCase() +
              getLanguage(file.name).slice(1)}
          </span>
          <span className="mx-2">|</span>
          <span>UTF-8</span>
          <span className="mx-2">|</span>
          <span>LF</span>
        </div>
      </div>

      <div ref={editorRef} className="flex-1 h-full"></div>
    </>
  );
};

export default Editor;
