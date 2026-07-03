import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { CircleHelp, Palette, Settings as SettingsIcon, ShieldCheck, Sparkles, UserCircle2 } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import { SkeletonCard } from "../components/ui/SkeletonLoader";

function toneLabel(value) {
  return value || "Not set";
}

export default function Settings() {
  const { username, isAuthenticated } = useAuth();
  const { themePreference, setThemePreference, themeOptions } = useTheme();
  const [profile, setProfile] = useState(null);
  const [personalization, setPersonalization] = useState(null);
  const [feedbackSummary, setFeedbackSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const isAdmin = username === "ayush2522";

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [profileResult, personalizationResult, feedbackResult] = await Promise.allSettled([
        api.profile.getOptional(),
        api.personalization.profile(),
        api.feedback.summary(),
      ]);

      if (profileResult.status === "fulfilled") setProfile(profileResult.value);
      else throw profileResult.reason;

      if (personalizationResult.status === "fulfilled") setPersonalization(personalizationResult.value);
      if (feedbackResult.status === "fulfilled") setFeedbackSummary(feedbackResult.value);
    } catch (err) {
      setError(err.message || "Failed to load settings.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const appPreferences = useMemo(
    () => [
      { label: "Preferred tone", value: toneLabel(profile?.preferred_tone) },
      { label: "Goal count", value: profile?.goals?.length ?? 0 },
      { label: "Interest count", value: profile?.interests?.length ?? 0 },
      { label: "Personalization status", value: personalization?.learning_status || "Unavailable" },
    ],
    [personalization, profile]
  );

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 grid gap-4 lg:grid-cols-2">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorState message={error} onRetry={loadData} />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6"
    >
      <section>
        <div className="flex items-center gap-2">
          <SettingsIcon className="h-5 w-5 text-accent" />
          <h1 className="text-2xl font-semibold text-white">Settings</h1>
        </div>
        <p className="mt-2 text-sm text-white/50">
          Review account status, profile-backed app preferences, and current developer access details.
        </p>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <section className="glass rounded-2xl p-5 lg:p-6">
          <div className="flex items-center gap-2">
            <UserCircle2 className="h-4 w-4 text-accent" />
            <h2 className="text-base font-semibold text-white">Account</h2>
          </div>
          <div className="mt-4 grid gap-3">
            <div className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-white/35">Username</p>
              <p className="mt-2 text-sm text-white/75">{username || "Unknown"}</p>
            </div>
            <div className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-white/35">Authentication</p>
              <p className="mt-2 text-sm text-white/75">{isAuthenticated ? "Authenticated" : "Signed out"}</p>
            </div>
          </div>
        </section>

        <section className="glass rounded-2xl p-5 lg:p-6">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-accent" />
            <h2 className="text-base font-semibold text-white">App preferences</h2>
          </div>
          <div className="mt-4 grid gap-3">
            {appPreferences.map((item) => (
              <div key={item.label} className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
                <p className="text-xs uppercase tracking-wide text-white/35">{item.label}</p>
                <p className="mt-2 text-sm text-white/75">{item.value}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <section className="glass rounded-2xl p-5 lg:p-6">
          <div className="flex items-center gap-2">
            <Palette className="h-4 w-4 text-accent" />
            <h2 className="text-base font-semibold text-white">Theme</h2>
          </div>
          <div className="mt-4 space-y-3">
            <p className="text-sm text-white/55">
              Theme preference is stored locally in this browser and applied globally across the app shell.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {themeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setThemePreference(option.value)}
                  className={`rounded-2xl border px-4 py-3 text-left transition-colors ${
                    themePreference === option.value
                      ? "border-accent/30 bg-accent/12"
                      : "border-white/8 bg-white/[0.03] hover:bg-white/[0.06]"
                  }`}
                >
                  <p className="text-sm font-medium text-white">{option.label}</p>
                  <p className="mt-1 text-xs text-white/45">
                    {option.value === "dark"
                      ? "Lock the interface to the current dark presentation."
                      : "Use the adaptive dark-safe palette and preserve browser theme preference."}
                  </p>
                </button>
              ))}
            </div>
            <div className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-white/35">Current preference</p>
              <p className="mt-2 text-sm text-white/75">
                {themeOptions.find((option) => option.value === themePreference)?.label || "System"}
              </p>
            </div>
          </div>
        </section>

        <section className="glass rounded-2xl p-5 lg:p-6">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-accent" />
            <h2 className="text-base font-semibold text-white">Developer access</h2>
          </div>
          <div className="mt-4 space-y-3">
            <div className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-white/35">Developer console visibility</p>
              <p className="mt-2 text-sm text-white/75">{isAdmin ? "Visible for this account" : "Hidden for this account"}</p>
            </div>
            <div className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-white/35">Feedback signals</p>
              <p className="mt-2 text-sm text-white/75">
                Generation: {feedbackSummary?.generation_quality?.total ?? 0} | Recommendations:{" "}
                {feedbackSummary?.recommendation_quality?.total ?? 0}
              </p>
            </div>
          </div>
        </section>
      </div>

      <section className="glass rounded-2xl p-5 lg:p-6">
        <div className="flex items-center gap-2">
          <CircleHelp className="h-4 w-4 text-accent" />
          <h2 className="text-base font-semibold text-white">Settings scope</h2>
        </div>
        <p className="mt-3 text-sm text-white/55">
          This page intentionally shows only real account and preference state already available from the current
          frontend session and backend profile/personalization endpoints.
        </p>
      </section>
    </motion.div>
  );
}
