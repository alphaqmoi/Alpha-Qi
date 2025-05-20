import { useState } from "react";

type DeploymentTarget = {
  id: string;
  name: string;
  icon: string;
  description: string;
};

type Deployment = {
  id: string;
  target: string;
  status: "building" | "success" | "failed";
  url?: string;
  timestamp: string;
};

const DeployPanel = () => {
  const [isDeploying, setIsDeploying] = useState(false);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  
  const deploymentTargets: DeploymentTarget[] = [
    { 
      id: "vercel", 
      name: "Vercel", 
      icon: "ri-vercel-fill", 
      description: "Deploy to Vercel for production" 
    },
    { 
      id: "railway", 
      name: "Railway", 
      icon: "ri-train-line", 
      description: "Deploy to Railway with full infrastructure" 
    },
    { 
      id: "github", 
      name: "GitHub Pages", 
      icon: "ri-github-fill", 
      description: "Deploy static sites to GitHub Pages" 
    }
  ];
  
  const deploymentHistory: Deployment[] = [
    {
      id: "1",
      target: "vercel",
      status: "success",
      url: "https://alpha-q-ai-project.vercel.app",
      timestamp: "2023-07-12 14:30"
    }
  ];
  
  const deploy = async () => {
    if (!selectedTarget) return;
    
    setIsDeploying(true);
    
    try {
      // Call deploy API
      await fetch("/api/deploy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target: selectedTarget })
      });
      
      // Success would be handled by polling the deployment status
    } catch (error) {
      console.error("Deployment error:", error);
    } finally {
      setIsDeploying(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-4 scrollbar-thin">
      <div>
        <h4 className="text-xs font-medium mb-2">Deploy Project</h4>
        <div className="space-y-2">
          {deploymentTargets.map((target) => (
            <div 
              key={target.id}
              className={`p-2 rounded border ${
                selectedTarget === target.id 
                  ? 'border-primary bg-primary bg-opacity-10' 
                  : 'border-gray-700 hover:border-gray-600'
              } cursor-pointer`}
              onClick={() => setSelectedTarget(target.id)}
            >
              <div className="flex items-center">
                <div className="w-6 h-6 mr-2 flex items-center justify-center">
                  <i className={`${target.icon} text-lg`}></i>
                </div>
                <div>
                  <h5 className="text-xs font-medium">{target.name}</h5>
                  <p className="text-xs text-gray-400">{target.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
        
        <button 
          className={`mt-3 px-4 py-2 text-xs font-medium rounded w-full ${
            selectedTarget && !isDeploying
              ? 'bg-primary hover:bg-primary-dark text-white' 
              : 'bg-gray-800 text-gray-400 cursor-not-allowed'
          }`}
          disabled={!selectedTarget || isDeploying}
          onClick={deploy}
        >
          {isDeploying ? (
            <span className="flex items-center justify-center">
              <i className="ri-loader-2-line animate-spin mr-1"></i> Deploying...
            </span>
          ) : 'Deploy Project'}
        </button>
      </div>
      
      <div>
        <h4 className="text-xs font-medium mb-2">Deployment History</h4>
        {deploymentHistory.length > 0 ? (
          <div className="space-y-2">
            {deploymentHistory.map((deployment) => (
              <div 
                key={deployment.id}
                className="p-2 rounded border border-gray-700 bg-gray-800"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center">
                    <i className={`${
                      deployment.target === "vercel" ? "ri-vercel-fill" :
                      deployment.target === "railway" ? "ri-train-line" :
                      "ri-github-fill"
                    } mr-1 text-sm`}></i>
                    <span className="text-xs font-medium">{
                      deployment.target.charAt(0).toUpperCase() + deployment.target.slice(1)
                    }</span>
                  </div>
                  <span className={`text-xs ${
                    deployment.status === "success" ? "text-green-400" :
                    deployment.status === "failed" ? "text-red-400" :
                    "text-yellow-400"
                  }`}>
                    {deployment.status.charAt(0).toUpperCase() + deployment.status.slice(1)}
                  </span>
                </div>
                {deployment.url && (
                  <a 
                    href={deployment.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline"
                  >
                    {deployment.url}
                  </a>
                )}
                <div className="text-xs text-gray-400 mt-1">
                  {deployment.timestamp}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 text-center">
            <p className="text-xs text-gray-400">No deployments yet</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DeployPanel;
