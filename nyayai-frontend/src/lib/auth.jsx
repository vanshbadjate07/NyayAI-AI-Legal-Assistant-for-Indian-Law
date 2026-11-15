import { createContext, useContext, useEffect, useState } from "react";

// MOCK AUTH — replace with real Google OAuth (e.g. @react-oauth/google)
// before launch. This simulates the login state machine (loading ->
// logged in, persisted across reloads) so the rest of the app — the
// gating logic, the modal, the navbar — can be built and tested now
// and only this file needs to change later.
const AuthContext = createContext(null);
const KEY = "nyayai_mock_user";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(KEY);
    if (stored) setUser(JSON.parse(stored));
    setLoading(false);
  }, []);

  function loginWithGoogle() {
    // TODO: swap for real Google OAuth flow. Simulated round-trip delay
    // so the UI (button spinner, modal close) behaves like the real thing.
    return new Promise((resolve) => {
      setTimeout(() => {
        const mockUser = { name: "Test User", email: "test.user@gmail.com" };
        localStorage.setItem(KEY, JSON.stringify(mockUser));
        setUser(mockUser);
        resolve(mockUser);
      }, 900);
    });
  }

  function logout() {
    localStorage.removeItem(KEY);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
