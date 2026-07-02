import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ListChecks, Check, Clock } from "lucide-react";
import { useFollowUps, groupFollowUps } from "../hooks/useFollowUps";
import { api } from "../api/client";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import { SkeletonCard } from "../components/ui/SkeletonLoader";

function FollowUpRow({ followUp, onComplete, onOpenContact }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="glass rounded-lg p-3 flex items-center justify-between gap-3"
    >
      <div className="min-w-0">
        <p className="text-sm text-white font-medium truncate">{followUp.title}</p>
        <div className="flex items-center gap-3 mt-1">
          {followUp.due_date && (
            <span className="text-xs text-white/40 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {new Date(followUp.due_date).toLocaleDateString()}
            </span>
          )}
          {followUp.contact_id && (
            <button
              onClick={() => onOpenContact(followUp.contact_id)}
              className="text-xs text-accent hover:underline"
            >
              View contact
            </button>
          )}
        </div>
      </div>
      <button
        onClick={() => onComplete(followUp.id)}
        className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 text-white/60 text-xs font-medium hover:bg-emerald-500/15 hover:text-emerald-400 transition-colors"
      >
        <Check className="w-3.5 h-3.5" />
        Done
      </button>
    </motion.div>
  );
}

function GroupSection({ title, items, onComplete, onOpenContact, accent }) {
  if (items.length === 0) return null;
  return (
    <div className="mb-6">
      <h2 className={`text-sm font-medium uppercase tracking-wide mb-3 ${accent || "text-white/50"}`}>
        {title} <span className="text-white/30 normal-case">({items.length})</span>
      </h2>
      <div className="flex flex-col gap-2">
        {items.map((f) => (
          <FollowUpRow key={f.id} followUp={f} onComplete={onComplete} onOpenContact={onOpenContact} />
        ))}
      </div>
    </div>
  );
}

export default function FollowUps() {
  const { followUps, loading, error, refetch } = useFollowUps();
  const navigate = useNavigate();
  const [completingId, setCompletingId] = useState(null);

  async function handleComplete(id) {
    setCompletingId(id);
    try {
      await api.followUps.update(id, { status: "completed" });
      refetch();
    } finally {
      setCompletingId(null);
    }
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-3">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorState message={error} onRetry={refetch} />
      </div>
    );
  }

  const groups = groupFollowUps(followUps);
  const hasAny = groups.overdue.length + groups.today.length + groups.upcoming.length + groups.noDate.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
    >
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-white">Follow-ups</h1>
        <p className="text-sm text-white/50 mt-1">What needs your attention.</p>
      </div>

      {!hasAny ? (
        <EmptyState
          icon={ListChecks}
          title="You're all caught up"
          description="No pending follow-ups. Add one from a contact's profile."
        />
      ) : (
        <>
          <GroupSection
            title="Overdue"
            items={groups.overdue}
            onComplete={handleComplete}
            onOpenContact={(id) => navigate(`/contacts/${id}`)}
            accent="text-red-400"
          />
          <GroupSection
            title="Today"
            items={groups.today}
            onComplete={handleComplete}
            onOpenContact={(id) => navigate(`/contacts/${id}`)}
            accent="text-accent"
          />
          <GroupSection
            title="Upcoming"
            items={groups.upcoming}
            onComplete={handleComplete}
            onOpenContact={(id) => navigate(`/contacts/${id}`)}
          />
          <GroupSection
            title="No due date"
            items={groups.noDate}
            onComplete={handleComplete}
            onOpenContact={(id) => navigate(`/contacts/${id}`)}
          />
        </>
      )}
    </motion.div>
  );
}