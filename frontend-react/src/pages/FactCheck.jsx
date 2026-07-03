import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, Copy, MessageSquareHeart, Search } from "lucide-react";
import { api } from "../api/client";
import Button from "../components/Button";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import { SkeletonCard, SkeletonLine } from "../components/ui/SkeletonLoader";

const exampleTopics = [
  "AI infrastructure market",
  "developer productivity metrics",
  "blockchain in healthcare",
];

const factCheckFeedbackOptions = [
  { key: "helpful", label: "Useful" },
  { key: "not_helpful", label: "Insufficient" },
  { key: "irrelevant", label: "Unclear" },
];

function buildFactCheckTargetId(query) {
  return `fact-check:${(query || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")}`;
}

export default function FactCheck() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [feedbackValue, setFeedbackValue] = useState("");
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [feedbackError, setFeedbackError] = useState("");

  const factCheckTargetId = useMemo(
    () => (result?.query ? buildFactCheckTargetId(result.query) : ""),
    [result]
  );

  async function handleCheck(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    setFeedbackValue("");
    setFeedbackMessage("");
    setFeedbackError("");
    if (!query.trim()) {
      setError("Please enter a topic to verify.");
      return;
    }

    setLoading(true);
    try {
      const data = await api.factCheck(query);
      setResult(data);
    } catch (err) {
      if (err.status === 429) {
        setError("Too many fact-checks in a row. Please wait a moment and try again.");
      } else {
        setError(err.message || "Something went wrong.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleFeedback(category) {
    if (!result?.query) return;
    setFeedbackSubmitting(true);
    setFeedbackError("");
    try {
      await api.submitFeedback({
        suggestion: result.query,
        category,
        target_type: "fact_check",
        target_id: factCheckTargetId,
        notes: result.summary ? result.summary.slice(0, 240) : undefined,
      });
      setFeedbackValue(category);
      setFeedbackMessage("Feedback saved");
      window.setTimeout(() => setFeedbackMessage(""), 1600);
    } catch (err) {
      setFeedbackError(err.message || "Could not save feedback right now.");
    } finally {
      setFeedbackSubmitting(false);
    }
  }

  async function handleCopy() {
    if (!result?.summary) return;
    try {
      await navigator.clipboard.writeText(result.summary);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6"
    >
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Search className="h-5 w-5 text-accent-secondary" />
            <h1 className="text-2xl font-semibold text-white">Fact Check</h1>
          </div>
          <p className="mt-2 text-sm text-white/50 max-w-3xl">
            Check a topic before you bring it into a meeting or outreach note. Nexora returns a concise verification
            summary you can review quickly.
          </p>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <section className="glass rounded-2xl p-5 lg:p-6">
          <div className="mb-4">
            <h2 className="text-base font-semibold text-white">Verification request</h2>
            <p className="mt-1 text-sm text-white/45">
              Use this when you want a quick sanity check before bringing up a company, trend, or topic in a meeting.
            </p>
          </div>

          <form onSubmit={handleCheck} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1.5">Topic to verify</label>
              <textarea
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                rows={4}
                placeholder="Example: recent trends in developer productivity platforms"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent-secondary/50 resize-none"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              {exampleTopics.map((topic) => (
                <button
                  key={topic}
                  type="button"
                  onClick={() => setQuery(topic)}
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/60 transition-colors hover:bg-white/10 hover:text-white"
                >
                  {topic}
                </button>
              ))}
            </div>

            {error ? <ErrorState message={error} /> : null}

            <div className="flex flex-wrap gap-2">
              <Button type="submit" icon={Search} loading={loading}>
                Run fact check
              </Button>
              {result ? (
                <Button type="button" variant="secondary" icon={Copy} onClick={handleCopy}>
                  {copied ? "Copied" : "Copy summary"}
                </Button>
              ) : null}
            </div>
          </form>
        </section>

        <section className="glass rounded-2xl p-5 lg:p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-white">What you'll see</h2>
            <p className="mt-1 text-sm text-white/45">
              This workspace stays focused on the details available for each check.
            </p>
          </div>

          <div className="rounded-xl border border-white/8 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-wide text-white/35">Confidence signal</p>
            <p className="mt-2 text-sm text-white/60">
              Nexora does not show a separate confidence score here, so use the summary as a quick sense check before
              you mention the topic.
            </p>
          </div>

          <div className="rounded-xl border border-white/8 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-wide text-white/35">Result format</p>
            <p className="mt-2 text-sm text-white/60">
              Results appear as a concise summary today, so this view is best for a fast verification pass rather than
              formal citation review.
            </p>
          </div>
        </section>
      </div>

      {loading ? (
        <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="glass rounded-2xl p-5 lg:p-6 space-y-3">
            <SkeletonLine width="40%" />
            <SkeletonLine width="75%" />
            <SkeletonLine width="60%" />
          </div>
          <SkeletonCard />
        </section>
      ) : null}

      {!loading && result ? (
        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="glass rounded-2xl p-5 lg:p-6"
        >
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="h-4 w-4" />
            <h2 className="text-base font-semibold">Verification summary</h2>
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-[0.7fr_1.3fr]">
            <div className="rounded-xl border border-white/8 bg-white/[0.03] p-4">
              <p className="text-xs uppercase tracking-wide text-white/35">Query</p>
              <p className="mt-2 text-sm text-white/75">{result.query}</p>
            </div>

            <div className="rounded-xl border border-white/8 bg-white/[0.03] p-4">
              <p className="text-xs uppercase tracking-wide text-white/35">Evidence summary</p>
              <p className="mt-2 text-sm leading-7 text-white/80">{result.summary}</p>
            </div>
          </div>

          <div className="mt-4 rounded-xl border border-white/8 bg-white/[0.03] p-4">
            <div className="flex flex-wrap items-center gap-2">
              <MessageSquareHeart className="h-4 w-4 text-accent-secondary" />
              <p className="text-sm font-medium text-white">Rate this fact check</p>
              <span className="text-xs text-white/35">This only records usefulness feedback for future product tuning.</span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {factCheckFeedbackOptions.map((option) => {
                const active = feedbackValue === option.key;
                return (
                  <button
                    key={option.key}
                    onClick={() => handleFeedback(option.key)}
                    disabled={feedbackSubmitting || active}
                    className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                      active
                        ? "border-accent-secondary/30 bg-accent-secondary/15 text-accent-secondary"
                        : feedbackSubmitting
                          ? "border-white/10 bg-white/5 text-white/35"
                          : "border-white/10 bg-white/5 text-white/55 hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
            {feedbackMessage ? <p className="mt-3 text-xs text-emerald-300">{feedbackMessage}</p> : null}
            {feedbackError ? <p className="mt-3 text-xs text-red-300">{feedbackError}</p> : null}
          </div>
        </motion.section>
      ) : null}

      {!loading && !result && !error ? (
        <EmptyState
          icon={Search}
          title="No fact-check yet"
          description="Verification summaries will appear here after a successful check."
        />
      ) : null}
    </motion.div>
  );
}
