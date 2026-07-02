import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { setUnauthorizedHandler } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [username, setUsername] = useState(() => localStorage.getItem("username") || null);
  const [token, setToken] = useState(() => localStorage.getItem("access_token") || null);
  const navigate = useNavigate();

  const login = useCallback((accessToken, user) => {
    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("username", user);
    setToken(accessToken);
    setUsername(user);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    setToken(null);
    setUsername(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      logout();
      navigate("/login", { replace: true });
    });
  }, [logout, navigate]);

  const isAuthenticated = Boolean(token);

  return (
    <AuthContext.Provider value={{ username, token, login, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}