import { useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, Tag, AlertCircle } from "lucide-react";
import { api } from "../api/client";
import Button from "../components/Button";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import { SkeletonCard, SkeletonLine } from "../components/ui/SkeletonLoader";

const examplePrompts = [
  { description: "AI for Sustainable Cities conference", interests: "climate change, urban planning" },
  { description: "Fintech and blockchain meetup", interests: "payments, decentralization" },
  { description: "Healthcare innovation summit", interests: "telemedicine, biotech" },
];

export default function Generate() {
  const [description, setDescription] = useState("");
  const [interests, setInterests] = useState("");
  const [themes, setThemes] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [feedbackGiven, setFeedbackGiven] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate(e) {
    e?.preventDefault();
    setError("");
    if (!description.trim() || !interests.trim()) {
      setError("Please fill in both the event description and your interests.");
      return;
    }
    const interestsList = interests
      .split(",")
      .map((i) => i.trim())
      .filter(Boolean);

    setLoading(true);
    setSuggestions([]);
    setThemes([]);
    setFeedbackGiven({});
    try {
      const data = await api.generateConversation(description, interestsList);
      setThemes(data.themes || []);
      setSuggestions(data.suggestions || []);
    } catch (err) {
      if (err.status === 429) {
        setError("You're generating too quickly. Please wait a moment and try again.");
      } else if (err.status === 401) {
        setError("Your session has expired. Please log out and log back in.");
      } else {
        setError(err.message || "Something went wrong.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleFeedback(suggestion, action) {
    try {
      await api.sendFeedback(suggestion, action);
      setFeedbackGiven((prev) => ({ ...prev, [suggestion]: action }));
    } catch {
      // Non-critical -- fail silently in UI, feedback just won't be recorded.
    }
  }

  function useExample(example) {
    setDescription(example.description);
    setInterests(example.interests);
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
    >
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="w-5 h-5 text-accent" />
          <h1 className="text-xl font-semibold text-white">Generate Conversation Starters</h1>
        </div>
        <p className="text-sm text-white/50">
          Tell us about the event and your interests — we'll craft personalized icebreakers.
        </p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="glass rounded-xl p-5 mb-6"
      >
        <form onSubmit={handleGenerate} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1.5">Event description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="e.g. AI for Sustainable Cities conference"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50 resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-white/70 mb-1.5">Your interests (comma-separated)</label>
            <input
              type="text"
              value={interests}
              onChange={(e) => setInterests(e.target.value)}
              placeholder="e.g. climate change, urban planning"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {examplePrompts.map((ex) => (
              <button
                type="button"
                key={ex.description}
                onClick={() => useExample(ex)}
                className="text-xs px-2.5 py-1.5 rounded-full bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors border border-white/10"
              >
                {ex.description}
              </button>
            ))}
          </div>

          {error && <ErrorState message={error} />}

          <Button type="submit" loading={loading} icon={Sparkles}>
            Generate Starters
          </Button>
        </form>
      </motion.div>

      {loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
          className="space-y-3"
        >
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </motion.div>
      )}

      {!loading && themes.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="glass rounded-xl p-5 mb-6"
        >
          <h3 className="text-sm font-medium text-white/70 flex items-center gap-2 mb-3">
            <Tag className="w-4 h-4 text-accent" />
            Detected Themes
          </h3>
          <div className="flex flex-wrap gap-2">
            {themes.map((t) => (
              <span
                key={t}
                className="px-2.5 py-1 rounded-full text-xs font-medium bg-accent/15 text-accent border border-accent/20"
              >
                {t}
              </span>
            ))}
          </div>
        </motion.div>
      )}

      {!loading && suggestions.length === 0 && themes.length === 0 && !error && (
        <EmptyState
          icon={Sparkles}
          title="No suggestions yet"
          description="Generate conversation starters to see suggestions appear here."
        />
      )}

      {!loading && suggestions.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
          <h3 className="text-sm font-medium text-white/70 mb-3">Suggested Conversation Starters</h3>
          <div className="flex flex-col gap-3">
            {suggestions.map((s, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: i * 0.04 }}
                className="glass rounded-lg p-4 flex items-start justify-between gap-4"
              >
                <p className="text-sm text-white/80 leading-relaxed flex-1">
                  <span className="text-accent font-semibold mr-2">{i + 1}.</span>
                  {s}
                </p>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button
                    onClick={() => handleFeedback(s, "like")}
                    className={`p-1.5 rounded-lg transition-colors ${
                      feedbackGiven[s] === "like"
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "text-white/30 hover:text-emerald-400 hover:bg-emerald-500/10"
                    }`}
                    title="Helpful"
                  >
                    <span className="text-lg">👍</span>
                  </button>
                  <button
                    onClick={() => handleFeedback(s, "dislike")}
                    className={`p-1.5 rounded-lg transition-colors ${
                      feedbackGiven[s] === "dislike"
                        ? "bg-red-500/20 text-red-400"
                        : "text-white/30 hover:text-red-400 hover:bg-red-500/10"
                    }`}
                    title="Not helpful"
                  >
                    <span className="text-lg">👎</span>
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}