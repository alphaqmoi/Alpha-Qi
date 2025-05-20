import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

type SidebarProps = {
  activePanel: "code" | "chat" | "voice" | "agent" | "deploy" | "settings";
  setActivePanel: (panel: "code" | "chat" | "voice" | "agent" | "deploy" | "settings") => void;
};

const Sidebar = ({ activePanel, setActivePanel }: SidebarProps) => {
  const menuItems = [
    { id: "code", icon: "ri-code-s-slash-line", label: "Files & Code" },
    { id: "chat", icon: "ri-message-3-line", label: "Chat" },
    { id: "voice", icon: "ri-mic-line", label: "Voice Assistant" },
    { id: "agent", icon: "ri-robot-line", label: "Agent" },
    { id: "deploy", icon: "ri-rocket-line", label: "Deploy" },
    { id: "settings", icon: "ri-settings-3-line", label: "Settings" }
  ];

  return (
    <aside className="w-16 bg-darker flex flex-col items-center py-4 border-r border-gray-800">
      <div className="mb-6">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white">
          <i className="ri-ai-generate text-xl"></i>
        </div>
      </div>
      
      <nav className="flex flex-col items-center space-y-6 mt-4">
        {menuItems.map((item) => (
          <TooltipProvider key={item.id}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button 
                  className={`w-10 h-10 flex items-center justify-center rounded ${activePanel === item.id ? 'bg-gray-800' : 'hover:bg-gray-800'} ${activePanel === item.id ? 'text-primary' : ''}`} 
                  title={item.label}
                  onClick={() => setActivePanel(item.id as any)}
                >
                  <i className={`${item.icon} text-xl`}></i>
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>{item.label}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ))}
      </nav>
      
      <div className="mt-auto">
        <button className="w-10 h-10 flex items-center justify-center rounded hover:bg-gray-800">
          <i className="ri-user-3-line text-xl"></i>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
