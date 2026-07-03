import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Calendar, MessageSquareHeart, Search, ThumbsDown, ThumbsUp } from "lucide-react";
import { api } from "../api/client";
import CustomSelect from "../components/ui/CustomSelect";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import { SkeletonCard } from "../components/ui/SkeletonLoader";

function formatDate(value) {
  if (!value) return "No timestamp";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function getSignal(entry) {
  return entry.category || entry.action || "unknown";
}

function getFeedbackTone(entry) {
  const signal = getSignal(entry);
  return ["helpful", "accepted", "like"].includes(signal) ? "positive" : "negative";
}

export default function FeedbackHistory() {
  const navigate = useNavigate();
  const [entries, setEntries] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [targetFilter, setTargetFilter] = useState("");

  useEffect(() => {
    Promise.all([api.getFeedbackHistory(), api.feedback.summary()])
      .then(([historyData, summaryData]) => {
        setEntries(historyData || []);
        setSummary(summaryData || null);
      })
      .catch((err) => setError(err.message || "Couldn't load feedback history."))
      .finally(() => setLoading(false));
  }, []);

  const targetOptions = useMemo(
    () =>
      [...new Set(entries.map((entry) => entry.target_type).filter(Boolean))].sort((a, b) =>
        a.localeCompare(b)
      ),
    [entries]
  );

  const targetSelectOptions = useMemo(
    () => [{ value: "", label: "All target types" }, ...targetOptions.map((option) => ({ value: option, label: option }))],
    [targetOptions]
  );

  const filteredEntries = useMemo(() => {
    let data = [...entries];

    if (query.trim()) {
      const search = query.trim().toLowerCase();
      data = data.filter((entry) =>
        [entry.suggestion, entry.category, entry.notes, entry.target_type, entry.target_id]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(search))
      );
    }

    if (targetFilter) {
      data = data.filter((entry) => entry.target_type === targetFilter);
    }

    return data;
  }, [entries, query, targetFilter]);

  const positiveCount = useMemo(
    () => filteredEntries.filter((entry) => getFeedbackTone(entry) === "positive").length,
    [filteredEntries]
  );
  const negativeCount = filteredEntries.length - positiveCount;
  const interactionFeedback = filteredEntries.filter((entry) => entry.target_type === "interaction");

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 grid gap-4 lg:grid-cols-3">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorState message={error} />
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
          <MessageSquareHeart className="h-5 w-5 text-accent-secondary" />
          <h1 className="text-2xl font-semibold text-white">Feedback History</h1>
        </div>
        <p className="mt-2 text-sm text-white/50">
          Review the feedback you've personally submitted so far. This now includes ratings from generated suggestions,
          recommendation cards, opportunity cards, and fact-check results, along with the preference signals that come
          from those actions.
        </p>
      </section>

      <div className="grid gap-4 lg:grid-cols-4">
        <div className="glass rounded-2xl p-4">
          <p className="text-sm text-white/45">Visible feedback items</p>
          <p className="mt-2 text-2xl font-semibold text-white">{filteredEntries.length}</p>
        </div>
        <div className="glass rounded-2xl p-4">
          <p className="text-sm text-white/45">Helpful signals</p>
          <p className="mt-2 text-2xl font-semibold text-emerald-300">{positiveCount}</p>
        </div>
        <div className="glass rounded-2xl p-4">
          <p className="text-sm text-white/45">Unhelpful signals</p>
          <p className="mt-2 text-2xl font-semibold text-red-300">{negativeCount}</p>
        </div>
        <div className="glass rounded-2xl p-4">
          <p className="text-sm text-white/45">Preferred categories</p>
          <p className="mt-2 text-sm text-white/70">
            {summary?.user_preferences?.preferred_feedback_categories?.length
              ? summary.user_preferences.preferred_feedback_categories.join(", ")
              : "Your strongest feedback patterns will appear here as you rate more suggestions"}
          </p>
        </div>
      </div>

      <section className="glass rounded-2xl p-4 lg:p-5 space-y-4">
        <div className="grid gap-3 lg:grid-cols-[1.5fr_1fr]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/30" />
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by suggestion text, category, note, or target"
              className="w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
            />
          </div>

          <CustomSelect
            value={targetFilter}
            onChange={setTargetFilter}
            options={targetSelectOptions}
            placeholder="All target types"
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-wide text-white/35">Generation quality</p>
            <p className="mt-2 text-sm text-white/70">
              {summary?.generation_quality?.total ?? 0} total signal(s)
            </p>
            <div className="mt-3 space-y-1 text-xs text-white/50">
              {Object.entries(summary?.generation_quality?.category_counts || {}).map(([key, value]) => (
                <p key={key}>
                  {key}: {value}
                </p>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-wide text-white/35">Recommendation feedback</p>
            <p className="mt-2 text-sm text-white/70">
              {summary?.recommendation_quality?.total ?? 0} total signal(s)
            </p>
            <div className="mt-3 space-y-1 text-xs text-white/50">
              {Object.entries(summary?.recommendation_quality?.category_counts || {}).map(([key, value]) => (
                <p key={key}>
                  {key}: {value}
                </p>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-wide text-white/35">Interaction feedback</p>
            {interactionFeedback.length ? (
              <div className="mt-2 space-y-1 text-sm text-white/70">
                <p>{interactionFeedback.length} interaction-linked feedback item(s)</p>
                <p className="text-xs text-white/50">
                  Interaction-linked feedback appears here when feedback is attached directly to an interaction.
                </p>
              </div>
            ) : (
              <p className="mt-2 text-sm text-white/50">
                No interaction-linked feedback yet.
              </p>
            )}
          </div>
        </div>
      </section>

      {!filteredEntries.length ? (
        <div className="glass rounded-2xl">
          <EmptyState
            icon={MessageSquareHeart}
            title="No feedback to show"
            description={
              entries.length
                ? "Try clearing the current filters."
                : "Rate a few generated suggestions, recommendation cards, opportunity cards, or fact-check results and your personal feedback signals will start to appear here."
            }
            actionLabel={entries.length ? "Clear filters" : "Open Generate"}
            onAction={
              entries.length
                ? () => {
                    setQuery("");
                    setTargetFilter("");
                  }
                : () => navigate("/generate")
            }
          />
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEntries.map((entry, index) => {
            const positive = getFeedbackTone(entry) === "positive";
            return (
              <motion.div
                key={`${entry.created_at}-${entry.suggestion}-${index}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: index * 0.03 }}
                className="glass rounded-2xl p-5"
              >
                <div className="flex items-start gap-3">
                  {positive ? (
                    <ThumbsUp className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <ThumbsDown className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                  )}

                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full border px-2.5 py-1 text-xs ${
                          positive
                            ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                            : "border-red-500/20 bg-red-500/10 text-red-300"
                        }`}
                      >
                        {getSignal(entry)}
                      </span>
                      {entry.target_type ? (
                        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-white/50">
                          {entry.target_type}
                        </span>
                      ) : null}
                      {entry.target_id ? (
                        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-white/50">
                          {entry.target_id}
                        </span>
                      ) : null}
                    </div>

                    <p className="mt-3 text-sm text-white/80">{entry.suggestion}</p>
                    {entry.notes ? <p className="mt-2 text-sm text-white/50">{entry.notes}</p> : null}

                    <div className="mt-3 flex items-center gap-2 text-xs text-white/35">
                      <Calendar className="h-3.5 w-3.5" />
                      {formatDate(entry.created_at)}
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
