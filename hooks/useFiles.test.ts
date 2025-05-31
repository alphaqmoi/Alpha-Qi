import { addFileToPath, deleteFileFromTree, type FileType } from "./useFiles";

describe("File Tree Helpers", () => {
  const initialFiles: FileType[] = [
    {
      id: "root",
      name: "root",
      type: "folder",
      children: [
        {
          id: "f1",
          name: "folder1",
          type: "folder",
          children: [],
        },
        {
          id: "file1",
          name: "file1.txt",
          type: "file",
          content: "hello",
        },
      ],
    },
  ];

  test("addFileToPath creates nested folders and adds file", () => {
    const newFile: FileType = {
      id: "newfile",
      name: "newfile.txt",
      type: "file",
      content: "new content",
    };
    const path = ["root", "folder2", "subfolder"];

    const result = addFileToPath(initialFiles, path, newFile);

    const rootFolder = result.find((f) => f.name === "root")!;
    const folder2 = rootFolder.children?.find((f) => f.name === "folder2");
    expect(folder2).toBeDefined();

    const subfolder = folder2?.children?.find((f) => f.name === "subfolder");
    expect(subfolder).toBeDefined();

    expect(subfolder?.children?.some((f) => f.id === "newfile")).toBe(true);
  });

  test("deleteFileFromTree deletes file by id", () => {
    const result = deleteFileFromTree(initialFiles, "file1");
    const root = result.find((f) => f.name === "root")!;
    expect(root.children?.some((f) => f.id === "file1")).toBe(false);
  });

  test("deleteFileFromTree deletes folder and its children", () => {
    const filesWithNested: FileType[] = [
      {
        id: "root",
        name: "root",
        type: "folder",
        children: [
          {
            id: "folderToDelete",
            name: "folderToDelete",
            type: "folder",
            children: [
              {
                id: "childFile",
                name: "child.txt",
                type: "file",
                content: "",
              },
            ],
          },
          {
            id: "otherFile",
            name: "other.txt",
            type: "file",
            content: "",
          },
        ],
      },
    ];

    const result = deleteFileFromTree(filesWithNested, "folderToDelete");
    const root = result.find((f) => f.name === "root")!;
    expect(root.children?.some((f) => f.id === "folderToDelete")).toBe(false);
    expect(root.children?.some((f) => f.name === "other.txt")).toBe(true);
  });
});
