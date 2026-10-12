import React, { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Code2, Loader2, AlertCircle } from "lucide-react";
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
    <div className="min-h-dvh bg-[#09090b] text-[#fafafa] flex flex-col justify-center items-center px-4 font-sans">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-4">
            <div className="size-10 rounded-lg bg-[#6366f1] flex items-center justify-center font-bold text-white shadow-lg shadow-[#6366f1]/20">
              <Code2 className="size-6" />
            </div>
            <span className="font-bold text-2xl tracking-tight text-white">RepoGPT</span>
          </Link>
          <h2 className="text-xl font-bold tracking-tight text-balance">Sign in to your account</h2>
          <p className="text-sm text-[#a1a1aa] mt-1 text-pretty">
            Access your indexed codebases and reviews
          </p>
        </div>

        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-6 shadow-xl">
          {serverError && (
            <div className="mb-4 p-3 rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/20 flex items-center gap-2 text-sm text-[#ef4444]">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{serverError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[#a1a1aa] mb-1.5">
                Email address
              </label>
              <input
                type="email"
                {...register("email")}
                placeholder="name@example.com"
                className="w-full bg-[#09090b] border border-[#27272a] focus:border-[#6366f1] focus:ring-1 focus:ring-[#6366f1] rounded-lg px-3 py-2 text-sm text-white placeholder-[#71717a] outline-none transition-all"
              />
              {errors.email && (
                <p className="mt-1 text-xs text-[#ef4444]">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-[#a1a1aa] mb-1.5">
                Password
              </label>
              <input
                type="password"
                {...register("password")}
                placeholder="••••••••••••"
                className="w-full bg-[#09090b] border border-[#27272a] focus:border-[#6366f1] focus:ring-1 focus:ring-[#6366f1] rounded-lg px-3 py-2 text-sm text-white placeholder-[#71717a] outline-none transition-all"
              />
              {errors.password && (
                <p className="mt-1 text-xs text-[#ef4444]">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 bg-[#6366f1] hover:bg-[#818cf8] text-white font-medium py-2.5 rounded-lg text-sm transition-all flex items-center justify-center gap-2 disabled:opacity-50"
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

          <div className="mt-6 pt-6 border-t border-[#27272a] text-center text-xs text-[#a1a1aa]">
            Don't have an account?{" "}
            <Link to="/register" className="text-[#6366f1] hover:underline font-medium">
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
