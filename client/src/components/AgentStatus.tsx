const AgentStatus = () => {
  return (
    <div className="h-1/3 border-t border-gray-800 flex flex-col overflow-hidden">
      <div className="px-4 py-2 bg-darker border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center">
          <h3 className="font-semibold text-sm">AGENT STATUS</h3>
          <div className="ml-2">
            <span className="agent-badge bg-green-500 bg-opacity-20 text-green-400">
              <i className="ri-checkbox-circle-fill mr-1 text-xs"></i> Ready
            </span>
          </div>
        </div>
        <div>
          <button className="p-1 rounded hover:bg-gray-800">
            <i className="ri-refresh-line text-sm"></i>
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-3 space-y-3 scrollbar-thin text-sm">
        <div>
          <h4 className="text-xs text-gray-400 mb-1">CURRENT TASK</h4>
          <div className="bg-gray-800 rounded p-2">
            <p className="text-xs">No active task</p>
            <div className="flex items-center mt-1">
              <div className="w-full bg-gray-700 rounded-full h-1.5">
                <div className="bg-primary h-1.5 rounded-full" style={{ width: '0%' }}></div>
              </div>
              <span className="ml-2 text-xs text-gray-400">0%</span>
            </div>
          </div>
        </div>
        
        <div>
          <h4 className="text-xs text-gray-400 mb-1">ACTION PLAN</h4>
          <ul className="space-y-1">
            <li className="flex items-start">
              <i className="ri-checkbox-blank-circle-line text-gray-500 mt-0.5 mr-2 text-xs"></i>
              <span className="text-xs">No tasks in queue</span>
            </li>
          </ul>
        </div>
        
        <div>
          <h4 className="text-xs text-gray-400 mb-1">RESOURCES</h4>
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <i className="ri-cpu-line mr-2 text-xs"></i>
                <span className="text-xs">CPU Usage</span>
              </div>
              <div className="flex items-center">
                <div className="w-16 bg-gray-700 rounded-full h-1.5 mr-2">
                  <div className="bg-green-500 h-1.5 rounded-full" style={{ width: '25%' }}></div>
                </div>
                <span className="text-xs text-gray-400">25%</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <i className="ri-hard-drive-line mr-2 text-xs"></i>
                <span className="text-xs">Memory</span>
              </div>
              <div className="flex items-center">
                <div className="w-16 bg-gray-700 rounded-full h-1.5 mr-2">
                  <div className="bg-green-500 h-1.5 rounded-full" style={{ width: '30%' }}></div>
                </div>
                <span className="text-xs text-gray-400">30%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="px-4 py-2 border-t border-gray-800 flex justify-between">
        <button className="px-3 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded flex items-center opacity-50 cursor-not-allowed">
          <i className="ri-stop-circle-line mr-1"></i> Stop Tasks
        </button>
        <button className="px-3 py-1 text-xs bg-primary hover:bg-primary-dark rounded flex items-center">
          <i className="ri-add-line mr-1"></i> New Task
        </button>
      </div>
    </div>
  );
};

export default AgentStatus;
