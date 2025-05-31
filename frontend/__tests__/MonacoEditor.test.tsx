import React from "react";
import { render, fireEvent, waitFor, act } from "@testing-library/react";
import MonacoEditor from "../components/MonacoEditor";
import renderer from "react-test-renderer"; // for snapshot test

const mockOnChangeFile = jest.fn();
const mockOnRemoveFile = jest.fn();

const mockEditorInstance = {
  onDidChangeModelContent: jest.fn((cb) => {
    setTimeout(cb, 0);
    return { dispose: jest.fn() };
  }),
  setModel: jest.fn(),
  getModel: jest.fn(() => ({
    getValue: jest.fn(() => "mock code"),
    uri: { toString: () => "file://mock" },
  })),
  getOption: jest.fn(() => 2),
  saveViewState: jest.fn(),
  restoreViewState: jest.fn(),
  focus: jest.fn(),
  dispose: jest.fn(),
};

jest.mock("monaco-editor", () => ({
  editor: {
    create: jest.fn(() => mockEditorInstance),
    setTheme: jest.fn(),
    getModel: jest.fn(() => null),
    createModel: jest.fn(() => ({
      getValue: () => "new file value",
    })),
    setModelMarkers: jest.fn(),
  },
  Uri: {
    parse: (uri: string) => ({ toString: () => uri }),
  },
  MarkerSeverity: { Error: 8 },
  Range: jest.fn().mockImplementation((sl, sc, el, ec) => ({
    startLineNumber: sl,
    startColumn: sc,
    endLineNumber: el,
    endColumn: ec,
  })),
}));

jest.mock("reconnecting-websocket", () =>
  jest.fn().mockImplementation(() => ({
    close: jest.fn(),
    onopen: null,
  })),
);

jest.mock("normalize-url", () => (url: string) => url);

const sendRequestMock = jest.fn(() =>
  Promise.resolve([
    {
      range: {
        start: { line: 0, character: 0 },
        end: { line: 0, character: 10 },
      },
      newText: "formatted",
    },
  ]),
);

const onNotificationMock = jest.fn();

jest.mock("monaco-languageclient", () => ({
  MonacoLanguageClient: jest.fn().mockImplementation(() => ({
    start: jest.fn(),
    stop: jest.fn(),
    onReady: jest.fn(() => Promise.resolve()),
    onNotification: onNotificationMock,
    sendRequest: sendRequestMock,
  })),
}));

jest.mock("vscode-ws-jsonrpc", () => ({
  WebSocketMessageReader: jest.fn(),
  WebSocketMessageWriter: jest.fn(),
}));

const mockFiles = [
  {
    uri: "file://mock",
    language: "javascript",
    value: "console.log('hello');",
  },
  {
    uri: "file://test2.py",
    language: "python",
    value: "print('world')",
  },
];

describe("MonacoEditor", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders without crashing", () => {
    const { getByText } = render(
      <MonacoEditor
        files={mockFiles}
        activeFileUri="file://mock"
        onChangeFile={mockOnChangeFile}
        onRemoveFile={mockOnRemoveFile}
        languageServerUrl="ws://localhost:3001"
      />,
    );
    expect(getByText("Format")).toBeInTheDocument();
  });

  it("calls onRemoveFile when 'Remove File' is clicked", () => {
    const { getByText } = render(
      <MonacoEditor
        files={mockFiles}
        activeFileUri="file://mock"
        onChangeFile={mockOnChangeFile}
        onRemoveFile={mockOnRemoveFile}
        languageServerUrl="ws://localhost:3001"
      />,
    );
    fireEvent.click(getByText("Remove File"));
    expect(mockOnRemoveFile).toHaveBeenCalledWith("file://mock");
  });

  it("displays save status", async () => {
    const { getByText } = render(
      <MonacoEditor
        files={mockFiles}
        activeFileUri="file://mock"
        onChangeFile={mockOnChangeFile}
        onRemoveFile={mockOnRemoveFile}
        languageServerUrl="ws://localhost:3001"
      />,
    );

    await waitFor(() => {
      expect(getByText(/Status:/)).toBeInTheDocument();
    });
  });

  it("calls onChangeFile when content changes", async () => {
    await act(async () => {
      render(
        <MonacoEditor
          files={mockFiles}
          activeFileUri="file://mock"
          onChangeFile={mockOnChangeFile}
          onRemoveFile={mockOnRemoveFile}
          languageServerUrl="ws://localhost:3001"
        />,
      );
    });

    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(mockOnChangeFile).toHaveBeenCalledWith("file://mock", "mock code");
  });

  it("calls languageClient.sendRequest for formatting", async () => {
    const { getByText } = render(
      <MonacoEditor
        files={mockFiles}
        activeFileUri="file://mock"
        onChangeFile={mockOnChangeFile}
        onRemoveFile={mockOnRemoveFile}
        languageServerUrl="ws://localhost:3001"
      />,
    );

    fireEvent.click(getByText("Format"));
    await waitFor(() => {
      expect(sendRequestMock).toHaveBeenCalledWith(
        "textDocument/formatting",
        expect.any(Object),
      );
    });
  });

  it("sets diagnostics when LSP publishes diagnostics", async () => {
    render(
      <MonacoEditor
        files={mockFiles}
        activeFileUri="file://mock"
        onChangeFile={mockOnChangeFile}
        onRemoveFile={mockOnRemoveFile}
        languageServerUrl="ws://localhost:3001"
      />,
    );

    const diagnostics = [
      {
        range: {
          start: { line: 0, character: 0 },
          end: { line: 0, character: 5 },
        },
        message: "Syntax error",
        source: "eslint",
        code: "no-undef",
      },
    ];

    const callback = onNotificationMock.mock.calls.find(
      ([method]) => method === "textDocument/publishDiagnostics",
    )?.[1];

    if (callback) {
      act(() => {
        callback({ uri: "file://mock", diagnostics });
      });
    }

    const monaco = require("monaco-editor");
    expect(monaco.editor.setModelMarkers).toHaveBeenCalled();
  });

  it("supports switching between files", async () => {
    const { rerender } = render(
      <MonacoEditor
        files={mockFiles}
        activeFileUri="file://mock"
        onChangeFile={mockOnChangeFile}
        onRemoveFile={mockOnRemoveFile}
        languageServerUrl="ws://localhost:3001"
      />,
    );

    rerender(
      <MonacoEditor
        files={mockFiles}
        activeFileUri="file://test2.py"
        onChangeFile={mockOnChangeFile}
        onRemoveFile={mockOnRemoveFile}
        languageServerUrl="ws://localhost:3001"
      />,
    );

    expect(mockEditorInstance.setModel).toHaveBeenCalled();
    expect(mockEditorInstance.restoreViewState).toHaveBeenCalled();
  });

  it("matches snapshot", () => {
    const tree = renderer
      .create(
        <MonacoEditor
          files={mockFiles}
          activeFileUri="file://mock"
          onChangeFile={mockOnChangeFile}
          onRemoveFile={mockOnRemoveFile}
          languageServerUrl="ws://localhost:3001"
        />,
      )
      .toJSON();

    expect(tree).toMatchSnapshot();
  });

  // New UI interaction tests

  it("focuses editor after tab switch", async () => {
    const { getByTestId } = render(
      <MonacoEditor
        files={mockFiles}
        activeFileUri="file://mock"
        onChangeFile={mockOnChangeFile}
        onRemoveFile={mockOnRemoveFile}
        languageServerUrl="ws://localhost:3001"
      />,
    );

    // Clear any previous calls to focus
    mockEditorInstance.focus.mockClear();

    const secondTab = getByTestId("tab-file://test2.py");
    fireEvent.click(secondTab);

    await waitFor(() => {
      expect(mockEditorInstance.focus).toHaveBeenCalled();
    });
  });

  it("disables 'Format' button if no active file", () => {
    const { getByText } = render(
      <MonacoEditor
        files={mockFiles}
        activeFileUri={null}
        onChangeFile={mockOnChangeFile}
        onRemoveFile={mockOnRemoveFile}
        languageServerUrl="ws://localhost:3001"
      />,
    );

    const formatBtn = getByText("Format");
    expect(formatBtn).toBeDisabled();
  });

  it("shows updated status message on save progress", async () => {
    const { getByText, rerender } = render(
      <MonacoEditor
        files={mockFiles}
        activeFileUri="file://mock"
        onChangeFile={mockOnChangeFile}
        onRemoveFile={mockOnRemoveFile}
        saveStatus="Status: Saving..."
        languageServerUrl="ws://localhost:3001"
      />,
    );

    expect(getByText("Status: Saving...")).toBeInTheDocument();

    rerender(
      <MonacoEditor
        files={mockFiles}
        activeFileUri="file://mock"
        onChangeFile={mockOnChangeFile}
        onRemoveFile={mockOnRemoveFile}
        saveStatus="Status: Saved"
        languageServerUrl="ws://localhost:3001"
      />,
    );

    expect(getByText("Status: Saved")).toBeInTheDocument();
  });
});
