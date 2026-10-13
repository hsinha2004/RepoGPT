import React, { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Loader2, AlertCircle } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { setAccessToken } from "../../api/client";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setServerError(null);
    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(data),
      });

      const resData = await response.json();
      if (!response.ok) {
        setServerError(resData.error?.message || "Invalid email or password");
        return;
      }

      setAccessToken(resData.access_token);
      setUser(resData.user);
      navigate("/app");
    } catch {
      setServerError("Unable to connect to server. Please try again.");
    }
  };

  return (
    <div className="min-h-dvh bg-zinc-50 text-zinc-900 flex flex-col justify-center items-center px-4 font-sans">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex flex-col items-center gap-2 mb-4 group">
            <img
              src="/logo-icon.png"
              alt="RepoGPT Logo"
              className="h-20 object-contain drop-shadow-md transition-transform hover:scale-105"
            />
            <span className="font-extrabold text-2xl tracking-tight text-zinc-950">
              Repo<span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-teal-500">GPT</span>
            </span>
          </Link>
          <h2 className="text-2xl font-bold tracking-tight text-zinc-950 text-balance">Sign in to your account</h2>
          <p className="text-sm text-zinc-600 mt-1 text-pretty">
            Access your indexed codebases and reviews
          </p>
        </div>

        <div className="bg-white border border-zinc-200 rounded-2xl p-7 shadow-xl shadow-zinc-200/50">
          {serverError && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 flex items-center gap-2 text-sm text-red-700">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{serverError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                Email address
              </label>
              <input
                type="email"
                {...register("email")}
                placeholder="name@example.com"
                className="w-full bg-zinc-50 border border-zinc-200 focus:bg-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 rounded-lg px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all"
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                Password
              </label>
              <input
                type="password"
                {...register("password")}
                placeholder="••••••••••••"
                className="w-full bg-zinc-50 border border-zinc-200 focus:bg-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 rounded-lg px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all"
              />
              {errors.password && (
                <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2.5 rounded-lg text-sm transition-all flex items-center justify-center gap-2 disabled:opacity-50 shadow-md shadow-emerald-600/20 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign In"
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-zinc-200 text-center text-xs text-zinc-600">
            Don't have an account?{" "}
            <Link to="/register" className="text-emerald-700 hover:text-emerald-800 font-semibold">
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
