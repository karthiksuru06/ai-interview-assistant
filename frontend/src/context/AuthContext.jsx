import React, { createContext, useContext, useState, useEffect } from "react";
import api from "../api/axios";

const AuthContext = createContext(null);

/**
 * Decode a JWT payload without verification.
 * Used only for extracting display data (sub, role) — NOT for security.
 */
function decodeJwtPayload(token) {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  // On mount: restore session from stored JWT (no /auth/me call needed)
  useEffect(() => {
    if (token) {
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      const payload = decodeJwtPayload(token);

      if (payload && payload.exp * 1000 > Date.now()) {
        setUser({
          id: payload.sub,
          role: payload.role || "student",
          username: payload.username || payload.email || payload.sub,
          email: payload.email || "",
        });
      } else {
        // Token expired or invalid
        localStorage.removeItem("token");
        setToken(null);
      }
    }
    setLoading(false);
  }, []);

  const login = async (emailOrUsername, password) => {
    // Backend expects JSON: { email: str, password: str }
    const response = await api.post("/auth/login", {
      email: emailOrUsername,
      password: password,
    });

    const { access_token, role } = response.data;
    localStorage.setItem("token", access_token);
    api.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
    setToken(access_token);

    const payload = decodeJwtPayload(access_token);
    const userData = {
      id: payload?.sub || "unknown",
      role: role || payload?.role || "student",
      username: payload?.username || emailOrUsername,
      email: payload?.email || emailOrUsername,
    };
    setUser(userData);
    return userData;
  };

  const signup = async (userData) => {
    // Backend returns { msg: "User created" } — no token
    await api.post("/auth/signup", userData);

    // Auto-login after successful signup
    const loginResponse = await api.post("/auth/login", {
      email: userData.email,
      password: userData.password,
    });

    const { access_token, role } = loginResponse.data;
    localStorage.setItem("token", access_token);
    api.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
    setToken(access_token);

    const payload = decodeJwtPayload(access_token);
    const newUser = {
      id: payload?.sub || "unknown",
      role: role || "student",
      username: payload?.username || userData.username,
      email: payload?.email || userData.email,
    };
    setUser(newUser);
    return newUser;
  };

  const logout = () => {
    localStorage.removeItem("token");
    delete api.defaults.headers.common["Authorization"];
    setToken(null);
    setUser(null);
  };

  const getSecurityQuestion = async (email) => {
    const response = await api.get(`/auth/security-question?email=${encodeURIComponent(email)}`);
    return response.data.security_question;
  };

  const resetPassword = async (email, securityAnswer, newPassword) => {
    // Backend expects: { email, security_answer, new_password }
    const response = await api.post("/auth/reset-password", {
      email: email,
      security_answer: securityAnswer,
      new_password: newPassword,
    });
    return response.data;
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!user,
    isAdmin: user?.role === "admin",
    login,
    signup,
    logout,
    getSecurityQuestion,
    resetPassword,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
