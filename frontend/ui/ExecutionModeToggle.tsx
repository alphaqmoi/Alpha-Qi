import React from "react";

export default function ExecutionModeToggle({
  mode,
  setMode,
}: {
  mode: string;
  setMode: (m: string) => void;
}) {
  return (
    <div className="mb-4">
      <label className="block font-semibold mb-1">Execution Mode</label>
      <select
        className="border rounded px-2 py-1"
        value={mode}
        onChange={(e) => setMode(e.target.value)}
      >
        <option value="auto">Auto</option>
        <option value="local-cpu">Local CPU</option>
        <option value="local-gpu">Local GPU</option>
        <option value="colab-gpu">Google Colab</option>
      </select>
    </div>
  );
}
