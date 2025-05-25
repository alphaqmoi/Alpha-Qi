// Colab API client for remote execution
import axios from 'axios';

const COLAB_API_URL = process.env.COLAB_API_URL || '';
const COLAB_API_KEY = process.env.COLAB_API_KEY || '';

export async function installExtension(name: string) {
  return axios.post(
    `${COLAB_API_URL}/install-extension`,
    { name },
    { headers: { 'x-api-key': COLAB_API_KEY } }
  );
}

export async function runModel(input_data: string, model_name: string) {
  return axios.post(
    `${COLAB_API_URL}/run-model`,
    { input_data, model_name },
    { headers: { 'x-api-key': COLAB_API_KEY } }
  );
}

export async function getStatus() {
  return axios.get(`${COLAB_API_URL}/get-status`, {
    headers: { 'x-api-key': COLAB_API_KEY },
  });
}
