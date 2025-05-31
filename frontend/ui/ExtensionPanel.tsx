import React from "react";

export default function ExtensionPanel({
  extensions,
  onInstall,
}: {
  extensions: string[];
  onInstall: (name: string) => void;
}) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 mb-4">
      <h3 className="font-semibold mb-2">Extensions</h3>
      <ul className="mb-2">
        {extensions.map((ext) => (
          <li key={ext} className="flex items-center justify-between py-1">
            <span>{ext}</span>
            <button
              className="text-xs bg-blue-600 text-white px-2 py-1 rounded"
              onClick={() => onInstall(ext)}
            >
              Reinstall
            </button>
          </li>
        ))}
      </ul>
      <button
        className="bg-green-600 text-white px-3 py-1 rounded"
        onClick={() => onInstall(prompt("Extension name:") || "")}
      >
        Install Extension
      </button>
    </div>
  );
}
