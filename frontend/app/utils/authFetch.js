import { useAuth } from "../hooks/useAuth";

// Hook-based fetch wrapper to include auth token
export function useAuthFetch() {
  const { user } = useAuth();

  const authFetch = async (url, options = {}) => {
    const token = user?.token;

    const headers = {
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      "Content-Type": "application/json",
    };

    const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}${url}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.error || "Request failed");
    }

    return res.json();
  };

  return authFetch;
}

/* ----------------- NON-HOOK VERSION FOR SCRIPTS ------------------ */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const PREDEFINED_USERS = import.meta.env.VITE_PREDEFINED_USERS;

/**
 * Parse the predefined users from env variable
 * Format: email:password:name,email:password:name,...
 * Returns a map { email: { password, name } }
 */
function parseEnvUsers() {
  if (!PREDEFINED_USERS) return {};

  const users = {};
  PREDEFINED_USERS.split(",").forEach((entry) => {
    const [email, password, name] = entry.split(":");
    if (email && password && name) {
      users[email] = { password, name };
    }
  });
  return users;
}

/**
 * Get user info from env by email
 * @param {string} email
 * @returns {{email:string, password:string, name:string} | null}
 */
function getEnvUser(email) {
  const users = parseEnvUsers();
  return users[email] ? { email, ...users[email] } : null;
}

/**
 * Fetch a real token by logging in to your API with email and password
 * @param {string} email
 * @param {string} password
 * @returns {Promise<string>} token
 */
async function getToken(email, password) {
  const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    let errorData = {};
    try {
      errorData = await res.json();
    } catch {}
    throw new Error(
      errorData.error || `Login failed with status ${res.status}`,
    );
  }

  const data = await res.json();

  if (data.status === "success" && data.token) {
    return data.token;
  }

  throw new Error(data.message || "Login failed, no token returned");
}

/**
 * Fetch wrapper using user credentials from env variable
 * @param {string} email - user email to authenticate as
 * @param {string} url - API endpoint path (e.g. "/models")
 * @param {object} options - fetch options
 * @returns {Promise<any>}
 */
export async function authFetchFromEnvUser(email, url, options = {}) {
  if (!API_BASE_URL)
    throw new Error("VITE_API_BASE_URL env variable is not set");

  const user = getEnvUser(email);
  if (!user) throw new Error(`No credentials found for ${email}`);

  const token = await getToken(user.email, user.password);
  if (!token) throw new Error("Failed to authenticate");

  const headers = {
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`,
  };

  // Set JSON content type if no FormData body and no Content-Type header
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorData = {};
    try {
      errorData = await res.json();
    } catch {}
    throw new Error(
      errorData.error || `Request failed with status ${res.status}`,
    );
  }

  return res.json();
}
