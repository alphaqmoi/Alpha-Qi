export async function getToken(email, password) {
  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    console.error("Login failed:", await res.text());
    return null;
  }

  const data = await res.json();
  return data.token;
}
