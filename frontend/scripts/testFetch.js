import { authFetchFromEnvUser } from "../utils/authFetch.js";

(async () => {
  try {
    const data = await authFetchFromEnvUser("victor@kwemoi.com", "/models");
    console.log("Data:", data);
  } catch (err) {
    console.error("Error:", err.message);
  }
})();
