import { useState, useCallback } from "react";
import { setAuthToken } from "../api/client";

export interface User {
  id: number;
  email: string;
  name: string;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);

  const login = useCallback((jwtToken: string, userData: User) => {
    setAuthToken(jwtToken);
    setTokenState(jwtToken);
    setUser(userData);
  }, []);

  const logout = useCallback(() => {
    setAuthToken(null);
    setTokenState(null);
    setUser(null);
  }, []);

  return {
    user,
    token,
    isAuthenticated: !!token,
    login,
    logout,
  };
}
