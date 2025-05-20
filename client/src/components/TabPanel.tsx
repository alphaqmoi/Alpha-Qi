type Tab = {
  id: string;
  label: string;
};

type TabPanelProps = {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: any) => void;
};

const TabPanel = ({ tabs, activeTab, onTabChange }: TabPanelProps) => {
  return (
    <div className="bg-darker border-b border-gray-800 flex">
      {tabs.map((tab) => (
        <button 
          key={tab.id}
          className={`px-4 py-2 text-xs font-medium ${
            activeTab === tab.id 
              ? 'border-b-2 border-primary' 
              : 'text-gray-400 hover:text-light'
          }`}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
};

export default TabPanel;
