import { FileType } from "@/hooks/useFiles";

type EditorTabsProps = {
  openedFiles: FileType[];
  activeFile: FileType | null;
  onTabClick: (fileId: string) => void;
  onTabClose: (fileId: string) => void;
};

const EditorTabs = ({ openedFiles, activeFile, onTabClick, onTabClose }: EditorTabsProps) => {
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

  return (
    <div className="flex bg-darker border-b border-gray-800">
      {openedFiles.map((file) => (
        <div 
          key={file.id}
          className={`px-4 py-2 flex items-center ${activeFile?.id === file.id ? 'tab-active' : 'hover:bg-gray-800'}`}
          onClick={() => onTabClick(file.id)}
        >
          <i className={`${getFileIcon(file.name)} mr-2`}></i>
          <span className="text-sm">{file.name}</span>
          <button 
            className="ml-2 p-1 rounded-full hover:bg-gray-700"
            onClick={(e) => {
              e.stopPropagation();
              onTabClose(file.id);
            }}
          >
            <i className="ri-close-line text-xs"></i>
          </button>
        </div>
      ))}
      <button className="px-3 border-l border-gray-800 hover:bg-gray-800">
        <i className="ri-add-line"></i>
      </button>
    </div>
  );
};

export default EditorTabs;
