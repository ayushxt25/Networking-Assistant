import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, Trash2, UserCircle2 } from "lucide-react";
import { api } from "../api/client";
import Button from "../components/Button";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import { SkeletonCard, SkeletonLine } from "../components/ui/SkeletonLoader";

function toCsv(value) {
  return Array.isArray(value) ? value.join(", ") : "";
}

function fromCsv(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildInitialForm(profile) {
  return {
    full_name: profile?.full_name || "",
    headline: profile?.headline || "",
    goals: toCsv(profile?.goals),
    interests: toCsv(profile?.interests),
    preferred_tone: profile?.preferred_tone || "",
  };
}

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [personalization, setPersonalization] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [firstTimeSetup, setFirstTimeSetup] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState("");
  const [form, setForm] = useState(buildInitialForm(null));

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSaveMessage("");
    try {
      const [profileResult, personalizationResult] = await Promise.allSettled([
        api.profile.getOptional(),
        api.personalization.profile(),
      ]);

      if (profileResult.status === "fulfilled") {
        if (profileResult.value) {
          setProfile(profileResult.value);
          setForm(buildInitialForm(profileResult.value));
          setFirstTimeSetup(false);
        } else {
          setProfile(null);
          setForm(buildInitialForm(null));
          setFirstTimeSetup(true);
        }
      } else {
        throw profileResult.reason;
      }

      if (personalizationResult.status === "fulfilled") {
        setPersonalization(personalizationResult.value);
      } else {
        setPersonalization(null);
      }
    } catch (err) {
      setError(err.message || "Failed to load profile.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const topPreferences = useMemo(
    () => personalization?.top_preferences || [],
    [personalization]
  );

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSaveMessage("");
    try {
      const updated = await api.profile.update({
        full_name: form.full_name || null,
        headline: form.headline || null,
        goals: fromCsv(form.goals),
        interests: fromCsv(form.interests),
        preferred_tone: form.preferred_tone || null,
      });
      setProfile(updated);
      setForm(buildInitialForm(updated));
      setFirstTimeSetup(false);
      setSaveMessage("Profile saved.");
      const latestPersonalization = await api.personalization.profile().catch(() => null);
      setPersonalization(latestPersonalization);
    } catch (err) {
      setError(err.message || "Failed to save profile.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    setSaveMessage("");
    try {
      await api.profile.remove();
      setProfile(null);
      setForm(buildInitialForm(null));
      setFirstTimeSetup(true);
      setSaveMessage("Profile cleared.");
    } catch (err) {
      setError(err.message || "Failed to delete profile.");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 grid gap-4 lg:grid-cols-2">
        <SkeletonCard />
        <div className="glass rounded-2xl p-5 lg:p-6 space-y-3">
          <SkeletonLine width="35%" />
          <SkeletonLine width="100%" />
          <SkeletonLine width="90%" />
          <SkeletonLine width="75%" />
        </div>
      </div>
    );
  }

  if (error && !profile && !firstTimeSetup) {
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
          <UserCircle2 className="h-5 w-5 text-accent" />
          <h1 className="text-2xl font-semibold text-white">Profile</h1>
        </div>
        <p className="mt-2 text-sm text-white/50">
          Maintain your networking profile, goals, interests, and preferred tone using the live backend profile model.
        </p>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="glass rounded-2xl p-5 lg:p-6">
          <div className="mb-4">
            <h2 className="text-base font-semibold text-white">
              {firstTimeSetup ? "Set up your profile" : "Edit profile"}
            </h2>
            <p className="mt-1 text-sm text-white/45">
              A `404 /profile` is treated as first-time setup, so this page can create the record on first save.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1.5">Full name</label>
              <input
                type="text"
                value={form.full_name}
                onChange={(event) => setForm((prev) => ({ ...prev, full_name: event.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
                placeholder="Your full name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-white/70 mb-1.5">Headline</label>
              <input
                type="text"
                value={form.headline}
                onChange={(event) => setForm((prev) => ({ ...prev, headline: event.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
                placeholder="What you want people to understand about you"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-white/70 mb-1.5">Goals</label>
              <textarea
                rows={3}
                value={form.goals}
                onChange={(event) => setForm((prev) => ({ ...prev, goals: event.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50 resize-none"
                placeholder="Comma-separated goals"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-white/70 mb-1.5">Interests</label>
              <textarea
                rows={3}
                value={form.interests}
                onChange={(event) => setForm((prev) => ({ ...prev, interests: event.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50 resize-none"
                placeholder="Comma-separated interests"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-white/70 mb-1.5">Preferred tone</label>
              <input
                type="text"
                value={form.preferred_tone}
                onChange={(event) => setForm((prev) => ({ ...prev, preferred_tone: event.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
                placeholder="Example: warm, concise, confident"
              />
            </div>

            {error ? <ErrorState message={error} /> : null}
            {saveMessage ? <p className="text-sm text-emerald-300">{saveMessage}</p> : null}

            <div className="flex flex-wrap gap-2">
              <Button type="submit" loading={saving} icon={Sparkles}>
                {firstTimeSetup ? "Create profile" : "Save changes"}
              </Button>
              {!firstTimeSetup ? (
                <Button type="button" variant="danger" loading={deleting} icon={Trash2} onClick={handleDelete}>
                  Delete profile
                </Button>
              ) : null}
            </div>
          </form>
        </section>

        <section className="space-y-4">
          <div className="glass rounded-2xl p-5 lg:p-6">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent" />
              <h2 className="text-base font-semibold text-white">Personalization summary</h2>
            </div>
            {personalization ? (
              <div className="mt-4 space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-white/35">Learning status</p>
                    <p className="mt-2 text-sm text-white/75">{personalization.learning_status}</p>
                  </div>
                  <div className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-white/35">Confidence</p>
                    <p className="mt-2 text-sm text-white/75">{Math.round((personalization.confidence_score || 0) * 100)}%</p>
                  </div>
                </div>

                <div className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
                  <p className="text-xs uppercase tracking-wide text-white/35">Top preferences</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {topPreferences.length ? (
                      topPreferences.map((item) => (
                        <span
                          key={item}
                          className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/60"
                        >
                          {item}
                        </span>
                      ))
                    ) : (
                      <span className="text-sm text-white/40">No personalization preferences yet.</span>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <EmptyState
                icon={Sparkles}
                title="No personalization summary yet"
                description="The backend did not return personalization data for this account yet."
              />
            )}
          </div>

          <div className="glass rounded-2xl p-5 lg:p-6">
            <h2 className="text-base font-semibold text-white">Profile-backed app fields</h2>
            <p className="mt-2 text-sm text-white/55">
              This page only edits fields supported by the real backend profile schema: full name, headline, goals,
              interests, and preferred tone.
            </p>
          </div>
        </section>
      </div>
    </motion.div>
  );
}
