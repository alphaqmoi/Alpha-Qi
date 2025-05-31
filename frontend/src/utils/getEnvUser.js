export function getEnvUser(email) {
  const envUsers = import.meta.env.VITE_PREDEFINED_USERS;
  if (!envUsers) return null;

  const users = envUsers.split(",").map((entry) => {
    const [email, password, name] = entry.split(":");
    return { email, password, name };
  });

  return users.find((u) => u.email === email) || null;
}
