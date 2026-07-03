import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Users2, Lock, User, AlertCircle, CheckCircle2 } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import Button from "../components/Button";
import GlassCard from "../components/GlassCard";
import { getAuthProvider, isSupabaseAuthProvider } from "../lib/authProvider";

export default function Login() {
  const [mode, setMode] = useState("login");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();
  const isSupabaseMode = isSupabaseAuthProvider();
  const identifierLabel = isSupabaseMode ? "Email" : "Username";
  const providerTitle = getAuthProvider() === "supabase" ? "Supabase Auth" : "Legacy Auth";

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    if (!identifier || !password) {
      setError(`Please enter both a ${identifierLabel.toLowerCase()} and password.`);
      return;
    }
    setLoading(true);
    try {
      if (isSupabaseMode) {
        await login(identifier, password);
      } else {
        const data = await api.login(identifier, password);
        await login(data.access_token, identifier);
      }
      navigate("/onboarding", { replace: true, state: { fromAuth: true } });
    } catch (err) {
      setError(err.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    if (!identifier || !password) {
      setError(`Please enter both a ${identifierLabel.toLowerCase()} and password.`);
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      await register(identifier, password);
      setSuccess(
        isSupabaseMode
          ? "Account created! Check your email if confirmation is required, then log in."
          : "Account created! You can now log in."
      );
      setMode("login");
      setPassword("");
    } catch (err) {
      setError(err.message || "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-bg bg-mesh flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-accent to-accent-secondary flex items-center justify-center mb-4 animate-glow">
            <Users2 className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">
            Networking<span className="gradient-text">Assistant</span>
          </h1>
          <p className="text-white/50 text-sm mt-1">Your AI-powered networking companion</p>
          <p className="text-white/35 text-xs mt-2 uppercase tracking-[0.2em]">{providerTitle}</p>
        </div>

        <GlassCard className="!p-8">
          <div className="flex gap-2 mb-6 p-1 bg-white/5 rounded-xl">
            <button
              onClick={() => {
                setMode("login");
                setError("");
                setSuccess("");
              }}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                mode === "login" ? "bg-accent text-white" : "text-white/60 hover:text-white"
              }`}
            >
              Log In
            </button>
            <button
              onClick={() => {
                setMode("register");
                setError("");
                setSuccess("");
              }}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                mode === "register" ? "bg-accent text-white" : "text-white/60 hover:text-white"
              }`}
            >
              Register
            </button>
          </div>

          {error && (
            <div className="flex items-center gap-2 px-4 py-3 mb-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}
          {success && (
            <div className="flex items-center gap-2 px-4 py-3 mb-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              {success}
            </div>
          )}

          <form onSubmit={mode === "login" ? handleLogin : handleRegister} className="space-y-4">
            <div>
              <label className="block text-sm text-white/60 mb-1.5">{identifierLabel}</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                <input
                  type={isSupabaseMode ? "email" : "text"}
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  className="w-full bg-bg-secondary border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                  placeholder={isSupabaseMode ? "you@example.com" : "your username"}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm text-white/60 mb-1.5">
                Password {mode === "register" && <span className="text-white/30">(min 8 characters)</span>}
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-bg-secondary border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                  placeholder="********"
                />
              </div>
            </div>

            <Button type="submit" loading={loading} className="w-full mt-2">
              {mode === "login" ? "Log In" : "Create Account"}
            </Button>
          </form>
        </GlassCard>
      </motion.div>
    </div>
  );
}
