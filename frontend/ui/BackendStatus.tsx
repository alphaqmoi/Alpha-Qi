import React from "react";

export default function BackendStatus({ status }: { status: any }) {
  return (
    <div className="bg-gray-900 rounded-lg p-4 mb-4 shadow">
      <h2 className="text-xl font-bold mb-2">System Info</h2>
      <ul className="text-sm">
        <li>
          Colab Status:{" "}
          {status?.colabConnected ? "🟢 Connected" : "🔴 Disconnected"}
        </li>
        <li>Extensions: {status?.extensions?.join(", ") || "None"}</li>
        <li>Execution Mode: {status?.executionMode || "Auto"}</li>
        <li>CPU: {status?.cpu || "N/A"}%</li>
        <li>
          RAM: {status?.memory?.used || "N/A"} /{" "}
          {status?.memory?.total || "N/A"}
        </li>
      </ul>
    </div>
  );
}
