const AUTH_PROVIDERS = new Set(["legacy", "supabase"]);

export function getAuthProvider() {
  const value = (import.meta.env.VITE_AUTH_PROVIDER || "legacy").trim().toLowerCase();
  return AUTH_PROVIDERS.has(value) ? value : "legacy";
}

export function isSupabaseAuthProvider() {
  return getAuthProvider() === "supabase";
}
