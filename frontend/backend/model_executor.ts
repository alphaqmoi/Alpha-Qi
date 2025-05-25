// Smart Executor: Decides whether to run locally or on Colab
import { getStatus, runModel } from './colab_client';

export async function getOptimalExecutionMode(system: { ram: number; cpu: number; gpu: boolean }) {
  if (system.ram < 4 || system.cpu > 70) return 'colab-gpu';
  if (system.gpu) return 'local-gpu';
  return 'local-cpu';
}

export async function executeModel({ input_data, model_name, system }) {
  const mode = await getOptimalExecutionMode(system);
  if (mode === 'colab-gpu') {
    return runModel(input_data, model_name);
  }
  // Local execution logic (stub)
  return { result: `Ran ${model_name} locally on ${input_data}` };
}
