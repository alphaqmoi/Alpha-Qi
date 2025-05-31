// __tests__/useCodeEditor.test.tsx
import { renderHook, act } from "@testing-library/react-hooks";
import * as monaco from "monaco-editor";
import { useCodeEditor } from "../hooks/useCodeEditor";

jest.mock("monaco-editor", () => {
  const listeners = new Set();
  return {
    editor: {
      create: jest.fn((container, options) => ({
        getModel: () => ({
          getValue: jest.fn(() => options.value),
          setValue: jest.fn(),
          getLanguageId: jest.fn(() => options.language),
          onDidChangeContent: jest.fn((cb) => {
            listeners.add(cb);
            return { dispose: () => listeners.delete(cb) };
          }),
        }),
        dispose: jest.fn(),
      })),
      setModelLanguage: jest.fn(),
    },
  };
});

describe("useCodeEditor", () => {
  it("initializes editor and calls onChange & debounced onAutoSave", () => {
    const containerRef = { current: document.createElement("div") };
    const onChange = jest.fn();
    const onAutoSave = jest.fn();

    jest.useFakeTimers();

    renderHook(() =>
      useCodeEditor({
        containerRef,
        value: "initial",
        language: "javascript",
        onChange,
        onAutoSave,
        autoSaveDebounceMs: 1000,
      }),
    );

    const editor = monaco.editor.create.mock.results[0].value;
    const model = editor.getModel();
    const contentChangeCallback = model.onDidChangeContent.mock.calls[0][0];

    act(() => {
      contentChangeCallback();
    });

    expect(onChange).toHaveBeenCalledWith("initial");
    expect(onAutoSave).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(onAutoSave).toHaveBeenCalledWith("initial");

    jest.useRealTimers();
  });
});
