const mockUndo = jest.fn();
const mockRedo = jest.fn();
const mockSearch = jest.fn();
const mockReplace = jest.fn();
const mockSaveViewState = jest.fn(() => ({ some: "state" }));
const mockRestoreViewState = jest.fn();
const mockCreateEditor = jest.fn();

export const useCodeEditor = jest.fn(() => ({
  editor: {}, // dummy editor object to be truthy
  undo: mockUndo,
  redo: mockRedo,
  search: mockSearch,
  replace: mockReplace,
  saveViewState: mockSaveViewState,
  restoreViewState: mockRestoreViewState,
  createEditor: mockCreateEditor,
}));
