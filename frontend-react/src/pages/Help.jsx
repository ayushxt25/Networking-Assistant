import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { CircleHelp, Compass, Lightbulb, MessageSquareHeart, Sparkles, Users2 } from "lucide-react";
import { useLocation } from "react-router-dom";
import { api } from "../api/client";
import CustomSelect from "../components/ui/CustomSelect";

function HelpCard({ icon: Icon, title, description, bullets }) {
  return (
    <section className="glass rounded-2xl p-5 lg:p-6">
      <div className="flex items-center gap-2">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-white/8 bg-white/5">
          <Icon className="h-4 w-4 text-accent" />
        </span>
        <h2 className="text-base font-semibold text-white">{title}</h2>
      </div>
      <p className="mt-3 text-sm text-white/55">{description}</p>
      <div className="mt-4 space-y-2">
        {bullets.map((item) => (
          <p key={item} className="text-sm text-white/70">
            {item}
          </p>
        ))}
      </div>
    </section>
  );
}

export default function Help() {
  const location = useLocation();
  const [signal, setSignal] = useState("helpful");
  const [feedbackCategory, setFeedbackCategory] = useState("general_feedback");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const feedbackCategoryOptions = useMemo(
    () => [
      { value: "bug", label: "Bug" },
      { value: "confusing", label: "Confusing" },
      { value: "feature_request", label: "Feature request" },
      { value: "general_feedback", label: "General feedback" },
      { value: "praise", label: "Praise" },
    ],
    []
  );

  const signalOptions = useMemo(
    () => [
      { value: "helpful", label: "Useful" },
      { value: "not_helpful", label: "Needs work" },
    ],
    []
  );

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) return;

    setSubmitting(true);
    setMessage("");
    setError("");

    const selectedCategory =
      feedbackCategoryOptions.find((option) => option.value === feedbackCategory)?.label || "General feedback";

    try {
      await api.submitFeedback({
        suggestion: `App feedback: ${selectedCategory}`,
        category: signal,
        target_type: "app_experience",
        target_id: location.pathname || "global",
        notes: notes.trim()
          ? `${selectedCategory}: ${notes.trim()}`
          : `${selectedCategory} feedback submitted from ${location.pathname || "global"}`,
      });
      setMessage("Feedback submitted");
      setNotes("");
    } catch (submitError) {
      setError(submitError.message || "Could not send feedback right now.");
    } finally {
      setSubmitting(false);
    }
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
          <CircleHelp className="h-5 w-5 text-accent" />
          <h1 className="text-2xl font-semibold text-white">Help</h1>
        </div>
        <p className="mt-2 text-sm text-white/50">
          A quick guide to the major sections of the app and how to use the product effectively.
        </p>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <HelpCard
          icon={Compass}
          title="Command Center"
          description="Use the Dashboard, Follow-ups, Recommendations, and Opportunities pages to understand what needs your attention next."
          bullets={[
            "Dashboard summarizes your current state across analytics, next-best actions, and network snapshots.",
            "Follow-ups help you execute on overdue, current, and upcoming relationship tasks.",
            "Recommendations and Opportunities surface real backend-generated actions and strategic openings.",
          ]}
        />

        <HelpCard
          icon={Users2}
          title="Relationships"
          description="Use Contacts, Contact Profiles, Events, and the Network Graph to understand people, context, and relationship structure."
          bullets={[
            "Contacts act as the CRM backbone for your network data.",
            "Contact Profile pages combine score, interactions, follow-ups, and related actions.",
            "Events and Network Graph add context around timing, clusters, and bridge connections.",
          ]}
        />

        <HelpCard
          icon={Sparkles}
          title="Prep Workspace"
          description="Use Generate, Fact Check, History, and Feedback History to prepare for conversations and refine output quality over time."
          bullets={[
            "Generate creates relationship preparation starters using your existing backend context.",
            "Fact Check verifies a topic before you bring it into a conversation.",
            "History and Feedback History help you reuse and improve what worked.",
          ]}
        />

        <HelpCard
          icon={Lightbulb}
          title="Insights"
          description="Use Relationship Scores, Analytics, and graph intelligence to prioritize your networking effort."
          bullets={[
            "Relationship Scores help you see who is strong, weak, risky, or strategic.",
            "Analytics summarizes contact, interaction, and follow-up health.",
            "Developer Console remains separate in the profile menu for internal debugging and observability.",
          ]}
        />
      </div>

      <section className="glass rounded-2xl p-5 lg:p-6">
        <div className="flex items-center gap-2">
          <MessageSquareHeart className="h-4 w-4 text-accent" />
          <h2 className="text-base font-semibold text-white">Product feedback</h2>
        </div>
        <p className="mt-3 text-sm text-white/55">
          Share bugs, confusing moments, feature requests, or general usefulness feedback. This is stored as real
          feedback for your account only.
        </p>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
            <div>
              <p className="text-xs uppercase tracking-wide text-white/35">Overall usefulness</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {signalOptions.map((option) => {
                  const active = signal === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setSignal(option.value)}
                      className={`rounded-2xl border px-4 py-3 text-left transition-colors ${
                        active
                          ? "border-accent/30 bg-accent/12"
                          : "border-white/8 bg-white/[0.03] hover:bg-white/[0.06]"
                      }`}
                    >
                      <p className="text-sm font-medium text-white">{option.label}</p>
                      <p className="mt-1 text-xs text-white/45">
                        {option.value === "helpful"
                          ? "Use this when the app experience is working well for you."
                          : "Use this when the app experience is blocked, unclear, or missing something important."}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <p className="text-xs uppercase tracking-wide text-white/35">Feedback category</p>
              <div className="mt-3">
                <CustomSelect
                  value={feedbackCategory}
                  onChange={setFeedbackCategory}
                  options={feedbackCategoryOptions}
                  placeholder="Select a category"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="text-xs uppercase tracking-wide text-white/35" htmlFor="app-feedback-notes">
              Notes
            </label>
            <textarea
              id="app-feedback-notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={4}
              placeholder="Share the issue, friction point, request, or what worked well."
              className="mt-3 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/30 focus:border-accent/50 focus:outline-none"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-xl bg-accent px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Submitting..." : "Submit feedback"}
            </button>
            {message ? <p className="text-sm text-emerald-300">{message}</p> : null}
            {error ? <p className="text-sm text-red-300">{error}</p> : null}
          </div>
        </form>
      </section>
    </motion.div>
  );
}
