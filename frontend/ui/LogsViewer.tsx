import React from 'react';

export default function LogsViewer({ logs }: { logs: string[] }) {
  return (
    <div className="bg-gray-900 rounded-lg p-4 mb-4 max-h-48 overflow-y-auto">
      <h3 className="font-semibold mb-2">Logs</h3>
      <ul className="text-xs font-mono">
        {logs.map((log, i) => (
          <li key={i}>{log}</li>
        ))}
      </ul>
    </div>
  );
}
