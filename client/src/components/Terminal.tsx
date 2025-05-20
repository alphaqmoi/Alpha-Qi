import { useState, useRef, useEffect } from "react";

const Terminal = () => {
  const [commandHistory, setCommandHistory] = useState<string[]>([
    "[INFO] Terminal ready"
  ]);
  const [currentCommand, setCurrentCommand] = useState("");
  const terminalRef = useRef<HTMLDivElement>(null);
  
  const executeCommand = async (command: string) => {
    if (!command.trim()) return;
    
    // Add command to history
    setCommandHistory(prev => [...prev, `$ ${command}`]);
    setCurrentCommand("");
    
    try {
      // Send command to backend
      const response = await fetch("/api/terminal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command })
      });
      
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Add result to history
      if (data.output) {
        setCommandHistory(prev => [...prev, data.output]);
      }
    } catch (error) {
      console.error("Error executing command:", error);
      setCommandHistory(prev => [...prev, "Error executing command. Please try again."]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      executeCommand(currentCommand);
    }
  };
  
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [commandHistory]);

  return (
    <>
      <div 
        ref={terminalRef}
        className="flex-1 bg-darker overflow-y-auto font-mono text-xs p-3 scrollbar-thin"
      >
        {commandHistory.map((line, index) => (
          <div key={index} className="terminal-text mb-1">
            {line.startsWith("$") ? (
              <span>
                <span className="text-green-400">$</span>{line.substring(1)}
              </span>
            ) : line.startsWith("[INFO]") ? (
              <span className="text-gray-400">{line}</span>
            ) : line.startsWith("[SUCCESS]") ? (
              <span className="text-green-400">{line}</span>
            ) : line.startsWith("[WARN]") ? (
              <span className="text-yellow-400">{line}</span>
            ) : line.startsWith("[ERROR]") ? (
              <span className="text-red-400">{line}</span>
            ) : (
              <span>{line}</span>
            )}
          </div>
        ))}
      </div>
      
      <div className="px-3 py-2 border-t border-gray-800 flex items-center">
        <span className="text-green-400 text-xs mr-2">$</span>
        <input 
          type="text" 
          className="flex-1 bg-darker text-light text-xs font-mono focus:outline-none" 
          placeholder="Enter command..."
          value={currentCommand}
          onChange={(e) => setCurrentCommand(e.target.value)}
          onKeyDown={handleKeyDown}
        />
      </div>
    </>
  );
};

export default Terminal;
