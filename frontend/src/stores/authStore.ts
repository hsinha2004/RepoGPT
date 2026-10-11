import { create } from "zustand";
import { setAccessToken } from "../api/client";

export interface User {
  id: string;
  email: string;
  name: string;
  role: "user" | "admin";
  is_active: boolean;
  github?: {
    id?: number;
    login?: string;
    avatar_url?: string;
  };
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  setUser: (user) => set({ user, isAuthenticated: !!user, isLoading: false }),
  logout: () => {
    setAccessToken(null);
    set({ user: null, isAuthenticated: false, isLoading: false });
  },
}));
