import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import FileExplorer from "@/components/FileExplorer";
import EditorTabs from "@/components/EditorTabs";
import Editor from "@/components/Editor";
import ChatInterface from "@/components/ChatInterface";
import AgentStatus from "@/components/AgentStatus";
import Terminal from "@/components/Terminal";
import ProjectPreview from "@/components/ProjectPreview";
import DeployPanel from "@/components/DeployPanel";
import TabPanel from "@/components/TabPanel";
import { useFiles } from "@/hooks/useFiles";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"terminal" | "preview" | "deploy">("terminal");
  const [activePanel, setActivePanel] = useState<"code" | "chat" | "voice" | "agent" | "deploy" | "settings">("chat");
  
  const { 
    files, 
    activeFile, 
    openFile, 
    updateFileContent,
    closeFile,
    openedFiles
  } = useFiles();

  return (
    <div className="flex h-screen bg-darker text-light font-sans overflow-hidden">
      <Sidebar activePanel={activePanel} setActivePanel={setActivePanel} />
      
      {activePanel === "code" && (
        <FileExplorer files={files} openFile={openFile} />
      )}
      
      <div className="flex-1 flex flex-col h-full">
        {openedFiles.length > 0 && (
          <EditorTabs 
            openedFiles={openedFiles}
            activeFile={activeFile}
            onTabClick={openFile}
            onTabClose={closeFile}
          />
        )}
        
        <div className="flex-1 flex h-full overflow-hidden">
          {activeFile && (
            <div className="flex-1 bg-dark overflow-hidden flex flex-col">
              <Editor 
                file={activeFile}
                onChange={(content) => updateFileContent(activeFile.id, content)}
              />
            </div>
          )}
          
          <div className="w-96 border-l border-gray-800 flex flex-col">
            <ChatInterface />
            
            <AgentStatus />
            
            <div className="h-1/3 border-t border-gray-800 flex flex-col overflow-hidden">
              <TabPanel
                activeTab={activeTab}
                onTabChange={setActiveTab}
                tabs={[
                  { id: "terminal", label: "Terminal" },
                  { id: "preview", label: "Preview" },
                  { id: "deploy", label: "Deploy" }
                ]}
              />
              
              {activeTab === "terminal" && <Terminal />}
              {activeTab === "preview" && <ProjectPreview />}
              {activeTab === "deploy" && <DeployPanel />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
