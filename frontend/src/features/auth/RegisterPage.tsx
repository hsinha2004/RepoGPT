import React, { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Loader2, AlertCircle } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { setAccessToken } from "../../api/client";

const registerSchema = z
  .object({
    name: z.string().min(2, "Name must be at least 2 characters"),
    email: z.string().email("Please enter a valid email address"),
    password: z.string().min(10, "Password must be at least 10 characters"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const passwordVal = watch("password", "");

  const onSubmit = async (data: RegisterFormData) => {
    setServerError(null);
    try {
      const response = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          name: data.name,
          email: data.email,
          password: data.password,
        }),
      });

      const resData = await response.json();
      if (!response.ok) {
        setServerError(resData.error?.message || "Registration failed. Please try again.");
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
    <div className="min-h-dvh bg-zinc-50 text-zinc-900 flex flex-col justify-center items-center px-4 font-sans py-12">
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
          <h2 className="text-2xl font-bold tracking-tight text-zinc-950 text-balance">Create your account</h2>
          <p className="text-sm text-zinc-600 mt-1 text-pretty">
            Get started with AI-driven repository intelligence
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
                Full Name
              </label>
              <input
                type="text"
                {...register("name")}
                placeholder="Ada Lovelace"
                className="w-full bg-zinc-50 border border-zinc-200 focus:bg-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 rounded-lg px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all"
              />
              {errors.name && (
                <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>
              )}
            </div>

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
                placeholder="At least 10 characters"
                className="w-full bg-zinc-50 border border-zinc-200 focus:bg-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 rounded-lg px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all"
              />
              {errors.password && (
                <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
              )}

              {/* Password strength indicator */}
              <div className="mt-2 flex items-center gap-1.5">
                <div
                  className={`h-1 flex-1 rounded-full transition-all ${
                    passwordVal.length >= 10 ? "bg-emerald-500" : "bg-zinc-200"
                  }`}
                />
                <div
                  className={`h-1 flex-1 rounded-full transition-all ${
                    passwordVal.length >= 14 ? "bg-emerald-500" : "bg-zinc-200"
                  }`}
                />
                <div
                  className={`h-1 flex-1 rounded-full transition-all ${
                    /[A-Z]/.test(passwordVal) && /[0-9]/.test(passwordVal) && passwordVal.length >= 10
                      ? "bg-emerald-500"
                      : "bg-zinc-200"
                  }`}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                Confirm Password
              </label>
              <input
                type="password"
                {...register("confirmPassword")}
                placeholder="Re-enter password"
                className="w-full bg-zinc-50 border border-zinc-200 focus:bg-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 rounded-lg px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all"
              />
              {errors.confirmPassword && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.confirmPassword.message}
                </p>
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
                  Creating account...
                </>
              ) : (
                "Create Account"
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-zinc-200 text-center text-xs text-zinc-600">
            Already have an account?{" "}
            <Link to="/login" className="text-emerald-700 hover:text-emerald-800 font-semibold">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
