import { useState, useRef } from "react";

const ProjectPreview = () => {
  const [isLoading, setIsLoading] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const handleIframeLoad = () => {
    setIsLoading(false);
  };

  const refreshPreview = () => {
    setIsLoading(true);
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src;
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <div className="px-3 py-2 border-b border-gray-800 flex items-center justify-between">
        <span className="text-xs">Project Preview</span>
        <button
          className="p-1 rounded hover:bg-gray-800"
          onClick={refreshPreview}
        >
          <i className="ri-refresh-line text-sm"></i>
        </button>
      </div>

      <div className="flex-1 relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-darker">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
          </div>
        )}

        <iframe
          ref={iframeRef}
          className="w-full h-full bg-white"
          src="/preview"
          onLoad={handleIframeLoad}
          title="Project Preview"
        ></iframe>
      </div>
    </div>
  );
};

export default ProjectPreview;
