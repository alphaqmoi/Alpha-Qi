import { useState } from "react";

export type FileType = {
  id: string;
  name: string;
  type: "file" | "folder";
  content?: string;
  children?: FileType[];
};

// Pure helper to add a file/folder to a nested path, creating folders if missing
export const addFileToPath = (
  filesArray: FileType[],
  pathParts: string[],
  newFile: FileType
): FileType[] => {
  if (pathParts.length === 0) return [...filesArray, newFile];

  const [currentPart, ...restParts] = pathParts;

  let found = filesArray.find(
    (f) => f.name === currentPart && f.type === "folder"
  );

  if (!found) {
    found = {
      id: `${currentPart}-${Date.now()}`,
      name: currentPart,
      type: "folder",
      children: [],
    };
    filesArray = [...filesArray, found];
  }

  const updatedChildren = addFileToPath(found.children ?? [], restParts, newFile);

  return filesArray.map((f) =>
    f.name === currentPart && f.type === "folder"
      ? { ...f, children: updatedChildren }
      : f
  );
};

// Pure helper to delete a file/folder by id from the tree
export const deleteFileFromTree = (
  filesArray: FileType[],
  fileId: string
): FileType[] => {
  return filesArray
    .filter((file) => file.id !== fileId)
    .map((file) => {
      if (file.type === "folder" && file.children) {
        return {
          ...file,
          children: deleteFileFromTree(file.children, fileId),
        };
      }
      return file;
    });
};

export const useFiles = () => {
  const [files, setFiles] = useState<FileType[]>([
    {
      id: "root",
      name: "root",
      type: "folder",
      children: [],
    },
  ]);
  const [activeFile, setActiveFile] = useState<FileType | null>(null);
  const [openedFiles, setOpenedFiles] = useState<FileType[]>([]);

  const openFile = (file: FileType) => {
    setActiveFile(file);
    setOpenedFiles((prev) => {
      if (prev.find((f) => f.id === file.id)) return prev;
      return [...prev, file];
    });
  };

  const closeFile = (fileId: string) => {
    setOpenedFiles((prev) => prev.filter((f) => f.id !== fileId));
    if (activeFile?.id === fileId) {
      setActiveFile(null);
    }
  };

  const updateFileContent = (fileId: string, newContent: string) => {
    const updateContentRecursive = (filesArray: FileType[]): FileType[] =>
      filesArray.map((file) => {
        if (file.id === fileId) {
          return { ...file, content: newContent };
        }
        if (file.type === "folder" && file.children) {
          return {
            ...file,
            children: updateContentRecursive(file.children),
          };
        }
        return file;
      });
    setFiles((prevFiles) => updateContentRecursive(prevFiles));
  };

  const createNewFileInPath = (path: string, newFile: FileType) => {
    const parts = path.split("/").filter(Boolean); // ["root", "folder1", ...]
    if (parts.length === 0) return;

    setFiles((prevFiles) => addFileToPath(prevFiles, parts, newFile));
  };

  const deleteFileById = (fileId: string) => {
    setFiles((prevFiles) => deleteFileFromTree(prevFiles, fileId));
    setOpenedFiles((prev) => prev.filter((f) => f.id !== fileId));
    if (activeFile?.id === fileId) {
      setActiveFile(null);
    }
  };

  return {
    files,
    activeFile,
    openedFiles,
    openFile,
    closeFile,
    updateFileContent,
    createNewFileInPath,
    deleteFileById,
  };
};
