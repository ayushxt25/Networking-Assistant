import { useState } from "react";
import { motion } from "framer-motion";
import { Search, CheckCircle2 } from "lucide-react";
import { api } from "../api/client";
import Button from "../components/Button";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import { SkeletonCard } from "../components/ui/SkeletonLoader";

export default function FactCheck() {
  const [query, setQuery] = useState("");
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCheck(e) {
    e.preventDefault();
    setError("");
    setSummary("");
    if (!query.trim()) {
      setError("Please enter a topic to verify.");
      return;
    }

    setLoading(true);
    try {
      const data = await api.factCheck(query);
      setSummary(data.summary);
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

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
    >
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <Search className="w-5 h-5 text-accent-secondary" />
          <h1 className="text-xl font-semibold text-white">Quick Fact Check</h1>
        </div>
        <p className="text-sm text-white/50">Verify a topic against Wikipedia before bringing it up.</p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="glass rounded-xl p-5 mb-6"
      >
        <form onSubmit={handleCheck} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1.5">Topic to verify</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. blockchain in healthcare"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent-secondary/50"
            />
          </div>

          {error && <ErrorState message={error} />}

          <Button type="submit" loading={loading} icon={Search}>
            Check Fact
          </Button>
        </form>
      </motion.div>

      {loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
        >
          <SkeletonCard />
        </motion.div>
      )}

      {!loading && summary && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="glass rounded-xl p-5"
        >
          <div className="flex items-center gap-2 mb-3 text-emerald-400">
            <CheckCircle2 className="w-4 h-4" />
            <h3 className="text-sm font-medium">Summary</h3>
          </div>
          <p className="text-sm text-white/80 leading-relaxed">{summary}</p>
        </motion.div>
      )}

      {!loading && !summary && !error && (
        <EmptyState
          icon={Search}
          title="No fact-check yet"
          description="Enter a topic to verify against Wikipedia."
        />
      )}
    </motion.div>
  );
}