import { createClient } from "@supabase/supabase-js";
import { getAuthProvider } from "./authProvider";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim() || "";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim() || "";

let client = null;

function canCreateSupabaseClient() {
  return getAuthProvider() === "supabase" && Boolean(supabaseUrl && supabaseAnonKey);
}

export function getSupabaseClient() {
  if (!canCreateSupabaseClient()) {
    return null;
  }

  if (!client) {
    client = createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });
  }

  return client;
}

export async function getSupabaseAccessToken() {
  const supabase = getSupabaseClient();
  if (!supabase) return null;

  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token || null;
}

export function getSupabaseConfigError() {
  if (getAuthProvider() !== "supabase") return null;
  if (!supabaseUrl || !supabaseAnonKey) {
    return "Supabase auth is enabled but VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY is missing.";
  }
  return null;
}
