import { getStatus, runModel } from "./colab_client";

type SystemInfo = {
  ram: number; // in GB
  cpu: number; // CPU usage percentage
  gpu: boolean; // GPU available or not
};

type ExecutionParams = {
  input_data: string; // Adjust this to match your actual input type
  model_name: string;
  system: SystemInfo;
};

// Determines the optimal mode of model execution
export async function getOptimalExecutionMode(
  system: SystemInfo,
): Promise<string> {
  if (system.ram < 4 || system.cpu > 70) return "colab-gpu";
  if (system.gpu) return "local-gpu";
  return "local-cpu";
}

// Executes model based on optimal execution mode
export async function executeModel({
  input_data,
  model_name,
  system,
}: ExecutionParams): Promise<{ result: string }> {
  const mode = await getOptimalExecutionMode(system);

  if (mode === "colab-gpu") {
    return runModel(input_data, model_name); // Assumes runModel returns { result: string }
  }

  // Stub for local execution
  return { result: `Ran ${model_name} locally on ${input_data}` };
}
