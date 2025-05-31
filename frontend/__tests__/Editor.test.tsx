import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import "@testing-library/jest-dom";
import Editor from "./Editor";

// Mock useCodeEditor before importing the component
jest.mock("@/hooks/useCodeEditor");

import { useCodeEditor } from "@/hooks/useCodeEditor";

// Access the mocked functions for assertions
const mockUndo = jest.fn();
const mockRedo = jest.fn();
const mockSearch = jest.fn();
const mockReplace = jest.fn();
const mockSaveViewState = jest.fn(() => ({ some: "state" }));
const mockRestoreViewState = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();

  (useCodeEditor as jest.Mock).mockReturnValue({
    editor: {},
    undo: mockUndo,
    redo: mockRedo,
    search: mockSearch,
    replace: mockReplace,
    saveViewState: mockSaveViewState,
    restoreViewState: mockRestoreViewState,
    createEditor: jest.fn(),
  });
});

const file = {
  name: "example.ts",
  content: "console.log('hello');",
};

describe("Editor component with mocked useCodeEditor", () => {
  it("renders and detects language from file extension", () => {
    const onChange = jest.fn();

    render(<Editor file={file} onChange={onChange} />);

    expect(screen.getByText("Typescript")).toBeInTheDocument();

    const saveBtn = screen.getByRole("button", { name: /save/i });
    expect(saveBtn).toBeEnabled();
  });

  it("calls undo when undo button clicked", () => {
    const onChange = jest.fn();

    render(<Editor file={file} onChange={onChange} />);

    const undoBtn = screen.getByTitle(/undo/i);

    fireEvent.click(undoBtn);

    expect(mockUndo).toHaveBeenCalled();
  });

  it("calls redo when redo button clicked", () => {
    const onChange = jest.fn();

    render(<Editor file={file} onChange={onChange} />);

    const redoBtn = screen.getByTitle(/redo/i);

    fireEvent.click(redoBtn);

    expect(mockRedo).toHaveBeenCalled();
  });

  it("calls search when search button clicked", () => {
    const onChange = jest.fn();

    render(<Editor file={file} onChange={onChange} />);

    const searchBtn = screen.getByTitle(/search/i);

    fireEvent.click(searchBtn);

    expect(mockSearch).toHaveBeenCalled();
  });

  it("calls replace when replace button clicked", () => {
    const onChange = jest.fn();

    render(<Editor file={file} onChange={onChange} />);

    const replaceBtn = screen.getByTitle(/replace/i);

    fireEvent.click(replaceBtn);

    expect(mockReplace).toHaveBeenCalled();
  });

  it("calls onSave when save button clicked", async () => {
    const onChange = jest.fn();
    const onSave = jest.fn(() => Promise.resolve());

    render(<Editor file={file} onChange={onChange} onSave={onSave} />);

    const saveBtn = screen.getByRole("button", { name: /save/i });

    await act(async () => {
      fireEvent.click(saveBtn);
    });

    expect(onSave).toHaveBeenCalled();
  });

  it("handles Ctrl+S keyboard shortcut to save", async () => {
    const onChange = jest.fn();
    const onSave = jest.fn(() => Promise.resolve());

    render(<Editor file={file} onChange={onChange} onSave={onSave} />);

    await act(async () => {
      fireEvent.keyDown(window, { code: "KeyS", ctrlKey: true });
    });

    expect(onSave).toHaveBeenCalled();
  });

  it("toggles theme when theme button clicked", () => {
    const onChange = jest.fn();

    render(<Editor file={file} onChange={onChange} />);

    const themeBtn = screen.getByTitle(/toggle theme/i);

    expect(themeBtn.querySelector("i.ri-sun-line")).toBeInTheDocument();

    fireEvent.click(themeBtn);

    expect(themeBtn.querySelector("i.ri-moon-line")).toBeInTheDocument();
  });
});
