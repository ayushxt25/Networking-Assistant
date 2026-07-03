import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  CalendarClock,
  Check,
  CheckCircle2,
  Clock,
  ListChecks,
  Plus,
  Search,
} from "lucide-react";
import { useFollowUps, groupFollowUps } from "../hooks/useFollowUps";
import { api } from "../api/client";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import Modal from "../components/ui/Modal";
import FollowUpForm from "../components/domain/FollowUpForm";
import { SkeletonCard } from "../components/ui/SkeletonLoader";

function formatDate(value) {
  if (!value) return "No due date";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function isCompletedStatus(status) {
  const normalized = (status || "").toLowerCase();
  return ["completed", "complete", "done", "closed"].includes(normalized);
}

function statusTone(status) {
  return isCompletedStatus(status)
    ? "bg-emerald-500/12 text-emerald-300 border-emerald-500/20"
    : "bg-white/5 text-white/65 border-white/10";
}

function FollowUpRow({ followUp, onComplete, completing, onOpenContact }) {
  const completeDisabled = completing || isCompletedStatus(followUp.status);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.18 }}
      className="rounded-xl border border-white/6 bg-white/[0.03] px-4 py-3 hover:bg-white/[0.05] transition-colors"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-white">{followUp.title}</p>
          {followUp.description && <p className="mt-1 text-sm text-white/55">{followUp.description}</p>}

          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-white/40">
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDate(followUp.due_date)}
            </span>
            <span className={`rounded-full border px-2 py-0.5 ${statusTone(followUp.status)}`}>
              {followUp.status}
            </span>
            {followUp.contact_id ? (
              <button
                onClick={() => onOpenContact(followUp.contact_id)}
                className="text-accent hover:text-accent-secondary transition-colors"
              >
                View contact
              </button>
            ) : null}
          </div>
        </div>

        <button
          onClick={() => onComplete(followUp)}
          disabled={completeDisabled}
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
            completeDisabled
              ? "border-white/10 bg-white/5 text-white/35"
              : "border-emerald-500/20 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/15"
          }`}
        >
          <Check className="h-3.5 w-3.5" />
          {completing ? "Saving..." : "Mark complete"}
        </button>
      </div>
    </motion.div>
  );
}

function GroupSection({ title, accent, items, completingId, onComplete, onOpenContact, emptyMessage }) {
  return (
    <section className="glass rounded-2xl p-5 lg:p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className={`text-sm font-medium uppercase tracking-wide ${accent}`}>
          {title} <span className="normal-case text-white/30">({items.length})</span>
        </h2>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-white/40">{emptyMessage}</p>
      ) : (
        <AnimatePresence mode="popLayout">
          <div className="space-y-3">
            {items.map((item) => (
              <FollowUpRow
                key={item.id}
                followUp={item}
                completing={completingId === item.id}
                onComplete={onComplete}
                onOpenContact={onOpenContact}
              />
            ))}
          </div>
        </AnimatePresence>
      )}
    </section>
  );
}

export default function FollowUps() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completingId, setCompletingId] = useState(null);
  const { followUps, loading, error, refetch } = useFollowUps();

  const visibleFollowUps = useMemo(() => {
    const search = query.trim().toLowerCase();
    if (!search) return followUps;
    return followUps.filter((item) =>
      [item.title, item.description, item.status]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(search))
    );
  }, [followUps, query]);

  const groups = groupFollowUps(visibleFollowUps);
  const hasAny =
    groups.overdue.length +
      groups.today.length +
      groups.upcoming.length +
      groups.noDate.length +
      groups.completed.length >
    0;

  async function handleComplete(followUp) {
    setCompletingId(followUp.id);
    try {
      await api.followUps.update(followUp.id, {
        title: followUp.title,
        description: followUp.description,
        due_date: followUp.due_date,
        contact_id: followUp.contact_id,
        event_id: followUp.event_id,
        status: "completed",
      });
      refetch();
    } finally {
      setCompletingId(null);
    }
  }

  async function handleCreate(payload) {
    setSubmitting(true);
    try {
      await api.followUps.create(payload);
      setCreateOpen(false);
      refetch();
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 grid gap-4 lg:grid-cols-2">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorState message={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6"
    >
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-accent" />
            <h1 className="text-2xl font-semibold text-white">Follow-ups</h1>
          </div>
          <p className="mt-2 text-sm text-white/50">
            Execute on relationship momentum with overdue, upcoming, and completed actions.
          </p>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-medium text-white hover:bg-accent/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add follow-up
        </button>
      </section>

      <section className="glass rounded-2xl p-4 lg:p-5 space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative lg:max-w-md w-full">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/30" />
            <input
              type="text"
              placeholder="Search titles, descriptions, or status"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
            />
          </div>

          <div className="flex flex-wrap gap-3 text-xs text-white/45">
            <span>{visibleFollowUps.length} visible</span>
            <span className="text-white/20">•</span>
            <span>{groups.overdue.length} overdue</span>
            <span className="text-white/20">•</span>
            <span>{groups.today.length} due today</span>
            <span className="text-white/20">•</span>
            <span>{groups.completed.length} completed</span>
          </div>
        </div>
      </section>

      {!hasAny ? (
        <div className="glass rounded-2xl">
          <EmptyState
            icon={ListChecks}
            title={query ? "No follow-ups match this search" : "No follow-ups yet"}
            description={
              query
                ? "Try a different search term."
                : "Create a follow-up here or from a contact profile to keep relationship actions organized."
            }
            actionLabel={query ? "Clear search" : "Add follow-up"}
            onAction={() => {
              if (query) {
                setQuery("");
                return;
              }
              setCreateOpen(true);
            }}
          />
        </div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-2">
          <GroupSection
            title="Overdue"
            accent="text-red-400"
            items={groups.overdue}
            completingId={completingId}
            onComplete={handleComplete}
            onOpenContact={(id) => navigate(`/contacts/${id}`)}
            emptyMessage="No overdue items."
          />
          <GroupSection
            title="Today"
            accent="text-amber-300"
            items={groups.today}
            completingId={completingId}
            onComplete={handleComplete}
            onOpenContact={(id) => navigate(`/contacts/${id}`)}
            emptyMessage="Nothing due today."
          />
          <GroupSection
            title="Upcoming"
            accent="text-white/55"
            items={groups.upcoming}
            completingId={completingId}
            onComplete={handleComplete}
            onOpenContact={(id) => navigate(`/contacts/${id}`)}
            emptyMessage="No upcoming follow-ups."
          />
          <GroupSection
            title="Completed"
            accent="text-emerald-300"
            items={groups.completed}
            completingId={completingId}
            onComplete={handleComplete}
            onOpenContact={(id) => navigate(`/contacts/${id}`)}
            emptyMessage="No completed items yet."
          />
          <GroupSection
            title="No due date"
            accent="text-white/55"
            items={groups.noDate}
            completingId={completingId}
            onComplete={handleComplete}
            onOpenContact={(id) => navigate(`/contacts/${id}`)}
            emptyMessage="Every open follow-up has a due date."
          />
        </div>
      )}

      <section className="glass rounded-2xl p-5 lg:p-6">
        <div className="flex items-center gap-2 mb-3">
          <CalendarClock className="h-4 w-4 text-accent" />
          <h2 className="text-base font-semibold text-white">Keep follow-ups organized</h2>
        </div>
        <p className="text-sm text-white/55 max-w-3xl">
          Follow-ups stay synced as you complete tasks, create new reminders from relationship context, and keep your
          next actions clear across contacts, events, and ongoing outreach.
        </p>
      </section>

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Add follow-up">
        <FollowUpForm
          onSubmit={handleCreate}
          onCancel={() => setCreateOpen(false)}
          submitting={submitting}
        />
      </Modal>
    </motion.div>
  );
}
