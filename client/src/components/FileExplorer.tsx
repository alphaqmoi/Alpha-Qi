import { useState } from "react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { FileType } from "@/hooks/useFiles";

type FileExplorerProps = {
  files: FileType[];
  openFile: (fileId: string) => void;
};

const FileExplorer = ({ files, openFile }: FileExplorerProps) => {
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    "root": true,
    "models": true,
  });

  const toggleFolder = (folderId: string) => {
    setExpandedFolders((prev) => ({
      ...prev,
      [folderId]: !prev[folderId]
    }));
  };

  const getFileIcon = (filename: string) => {
    const extension = filename.split('.').pop()?.toLowerCase();
    
    if (extension === 'py') return "ri-file-code-line text-blue-400";
    if (extension === 'js' || extension === 'jsx' || extension === 'ts' || extension === 'tsx') return "ri-file-code-line text-yellow-400";
    if (extension === 'json') return "ri-file-code-line text-orange-400";
    if (extension === 'html') return "ri-file-code-line text-red-400";
    if (extension === 'css') return "ri-file-code-line text-blue-300";
    if (extension === 'env') return "ri-file-lock-line text-green-400";
    
    return "ri-file-line";
  };

  const renderFile = (file: FileType) => {
    return (
      <div 
        key={file.id}
        className="flex items-center px-2 py-1 rounded hover:bg-gray-800 cursor-pointer"
        onClick={() => openFile(file.id)}
      >
        <i className={`${getFileIcon(file.name)} mr-2`}></i>
        <span className="text-sm">{file.name}</span>
      </div>
    );
  };

  const renderFolder = (folder: FileType) => {
    const isExpanded = expandedFolders[folder.id] || false;
    
    return (
      <div key={folder.id}>
        <Collapsible open={isExpanded} onOpenChange={() => toggleFolder(folder.id)}>
          <CollapsibleTrigger className="w-full">
            <div className="flex items-center px-2 py-1 rounded hover:bg-gray-800 cursor-pointer">
              <i className={`${isExpanded ? 'ri-arrow-down-s-line' : 'ri-arrow-right-s-line'} mr-1 text-sm`}></i>
              <i className="ri-folder-line mr-2 text-yellow-500"></i>
              <span className="text-sm">{folder.name}</span>
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="ml-4 mt-1">
              {folder.children?.map((child) => 
                child.type === 'folder' ? renderFolder(child) : renderFile(child)
              )}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    );
  };

  return (
    <div className="w-56 bg-darker border-r border-gray-800 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <h3 className="font-semibold text-sm">FILES</h3>
        <div className="flex space-x-1">
          <button className="p-1 rounded hover:bg-gray-800" title="New File">
            <i className="ri-add-line text-sm"></i>
          </button>
          <button className="p-1 rounded hover:bg-gray-800" title="New Folder">
            <i className="ri-folder-add-line text-sm"></i>
          </button>
          <button className="p-1 rounded hover:bg-gray-800" title="Refresh">
            <i className="ri-refresh-line text-sm"></i>
          </button>
        </div>
      </div>
      
      <div className="overflow-y-auto flex-1 scrollbar-thin">
        <div className="py-2">
          {files.map((file) => 
            file.type === 'folder' ? renderFolder(file) : renderFile(file)
          )}
        </div>
      </div>
    </div>
  );
};

export default FileExplorer;
