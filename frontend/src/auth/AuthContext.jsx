import { createContext, useContext, useEffect, useState } from "react";

import { api, request, setUnauthorizedHandler, tokenStorage } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // If a token is saved from before a refresh, we must ask the backend who it belongs to.
  const [checking, setChecking] = useState(() => Boolean(tokenStorage.get()));
  // A message for the login page, e.g. "Your session has expired...".
  const [notice, setNotice] = useState("");

  // Any 401 from the backend (expired or invalid token) logs the user out.
  // We only clear the user: ProtectedRoute then sends them to /login and
  // remembers which page they were on.
  useEffect(() => {
    setUnauthorizedHandler((message) => {
      setNotice(message);
      setUser(null);
    });
  }, []);

  // After a page refresh: turn the saved token back into a user.
  useEffect(() => {
    if (!tokenStorage.get()) return;
    api
      .get("/api/auth/me")
      .then(setUser)
      .catch(() => tokenStorage.clear())
      .finally(() => setChecking(false));
  }, []);

  async function login(email, password) {
    const result = await request("/api/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    tokenStorage.set(result.access_token);
    setNotice("");
    setUser(result.user);
    return result.user;
  }

  async function register({ fullName, email, password }) {
    await request("/api/auth/register", {
      method: "POST",
      body: { full_name: fullName, email, password },
      auth: false,
    });
    return login(email, password); // sign straight in after creating the account
  }

  function logout() {
    tokenStorage.clear();
    setNotice("You have been logged out.");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, checking, notice, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>.");
  return context;
}
