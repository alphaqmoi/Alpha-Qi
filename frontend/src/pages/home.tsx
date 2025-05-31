"use client";

import React, { useState, useRef } from "react";
import dynamic from "next/dynamic";

import Sidebar from "@/components/Sidebar";
import FileExplorer from "@/components/FileExplorer";
import EditorTabs from "@/components/EditorTabs";
import ChatInterface from "@/components/ChatInterface";
import AgentStatus from "@/components/AgentStatus";
import Terminal from "@/components/Terminal";
import ProjectPreview from "@/components/ProjectPreview";
import DeployPanel from "@/components/DeployPanel";
import TabPanel from "@/components/TabPanel";
import { useFiles } from "@/hooks/useFiles";

import { useMonacoLspEditor } from "@/hooks/useMonacoLspEditor";

// 🔁 Dynamically import Editor with SSR disabled
// Note: We replace this Editor with our own editor container managed by useMonacoLspEditor, so no need to import here.

export default function Home() {
  const containerRef = useRef<HTMLDivElement>(null);

  const [activeTab, setActiveTab] = useState<"terminal" | "preview" | "deploy">(
    "terminal",
  );
  const [activePanel, setActivePanel] = useState<
    "code" | "chat" | "voice" | "agent" | "deploy" | "settings"
  >("chat");

  const {
    files,
    activeFile,
    openFile,
    updateFileContent,
    closeFile,
    openedFiles,
  } = useFiles();

  // We expect your useFiles to provide files with at least these fields:
  // { id: string (uri), language: string, content: string }
  // Adjust below if needed to match your actual data shape.

  const activeFileUri = activeFile?.id || "";

  const filesForEditor = files.map((f) => ({
    uri: f.id,
    language: f.language || "plaintext",
    value: f.content,
  }));

  const onChangeFile = (uri: string, newValue: string) => {
    updateFileContent(uri, newValue);
  };

  const onRemoveFile = (uri: string) => {
    closeFile(uri);
    if (activeFileUri === uri && filesForEditor.length > 1) {
      const nextFile = filesForEditor.find((f) => f.uri !== uri);
      if (nextFile) openFile(nextFile.uri);
    }
  };

  const { diagnosticsMap, saveStatus, formatFile, removeFile } =
    useMonacoLspEditor({
      containerRef,
      files: filesForEditor,
      activeFileUri,
      onChangeFile,
      onRemoveFile,
      languageServerUrl: "ws://localhost:3001",
      theme: "vs-dark",
    });

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
            // Add diagnostics error counts to tabs:
            renderExtra={(file) =>
              diagnosticsMap[file.id]?.length > 0 ? (
                <span className="ml-2 text-red-500 font-bold">
                  {diagnosticsMap[file.id].length}
                </span>
              ) : null
            }
          />
        )}

        <div className="flex-1 flex flex-col h-full overflow-hidden">
          <div className="flex-shrink-0 p-2 bg-gray-900 flex items-center gap-3">
            <button
              className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded"
              onClick={formatFile}
              disabled={!activeFileUri}
            >
              Format File
            </button>

            <button
              className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded"
              onClick={removeFile}
              disabled={!activeFileUri}
            >
              Delete File
            </button>

            <span className="text-sm text-gray-400 ml-4">{saveStatus}</span>
          </div>

          <div
            ref={containerRef}
            style={{ flexGrow: 1, position: "relative", minHeight: 0 }}
            className="bg-gray-900"
          />

          {!activeFileUri && (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500 pointer-events-none">
              No file selected
            </div>
          )}
        </div>

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
                { id: "deploy", label: "Deploy" },
              ]}
            />

            {activeTab === "terminal" && <Terminal />}
            {activeTab === "preview" && <ProjectPreview />}
            {activeTab === "deploy" && <DeployPanel />}
          </div>
        </div>
      </div>
    </div>
  );
}
