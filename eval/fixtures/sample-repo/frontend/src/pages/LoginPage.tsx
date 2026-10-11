import React, { useState } from "react";
import { apiFetch } from "../api/client";
import { User } from "../auth/useAuth";

interface LoginPageProps {
  onLoginSuccess: (token: string, user: User) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      // Fetch user profile or mock user payload
      const mockUser: User = { id: 1, email, name: email.split("@")[0] };
      onLoginSuccess(res.access_token, mockUser);
    } catch (err: any) {
      setError(err.message || "Login failed");
    }
  };

  return (
    <div className="login-container">
      <h2>Sign in to TaskFlow</h2>
      {error && <div className="error-banner">{error}</div>}
      <form onSubmit={handleSubmit}>
        <label>
          Email:
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password:
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button type="submit">Log In</button>
      </form>
    </div>
  );
};
