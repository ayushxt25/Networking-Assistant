import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  BadgeCheck,
  ArrowUpDown,
  CalendarClock,
  CheckCircle2,
  MessageSquareX,
  Plus,
  Search,
  Sparkles,
  Target,
  Users2,
} from "lucide-react";
import { api } from "../api/client";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import Modal from "../components/ui/Modal";
import FollowUpForm from "../components/domain/FollowUpForm";
import ScoreBadge from "../components/ui/ScoreBadge";
import { SkeletonCard } from "../components/ui/SkeletonLoader";

function formatDate(value) {
  if (!value) return "No date";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function priorityTone(score) {
  if (score >= 85) return "text-red-300 bg-red-500/10 border-red-500/20";
  if (score >= 70) return "text-amber-300 bg-amber-500/10 border-amber-500/20";
  return "text-emerald-300 bg-emerald-500/10 border-emerald-500/20";
}

function getLifecycleTone(status) {
  if (status === "accepted") return "text-emerald-300 bg-emerald-500/10 border-emerald-500/20";
  if (status === "dismissed") return "text-red-300 bg-red-500/10 border-red-500/20";
  if (status === "completed") return "text-sky-300 bg-sky-500/10 border-sky-500/20";
  if (status === "converted_to_follow_up") return "text-violet-300 bg-violet-500/10 border-violet-500/20";
  return "text-white/55 bg-white/5 border-white/10";
}

function getOpportunitySection(type) {
  if (type === "activate_bridge_contact") return "Warm introductions";
  if (["reconnect_with_cold_contact", "revive_weak_tie"].includes(type)) return "Reconnection opportunities";
  if (["strengthen_strategic_contact", "nurture_high_score_relationship"].includes(type)) {
    return "Relationship growth opportunities";
  }
  if (type === "prepare_for_upcoming_event") return "Event-related opportunities";
  return "Priority opportunities";
}

function inferredStatus(item, followUpMap) {
  if (!item.related_follow_up_id) return "No linked follow-up";
  const followUp = followUpMap.get(item.related_follow_up_id);
  return followUp?.status || "Linked follow-up unavailable";
}

function OpportunityCard({
  item,
  contactName,
  relationshipScore,
  lifecycleStatus,
  followUpStatusLabel,
  onAccept,
  onOpenContact,
  onDismiss,
  onComplete,
  onConvert,
  onGenerate,
  accepting,
  dismissing,
  completing,
}) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22 }}
      className="glass rounded-2xl p-5 hover:border-white/12 transition-colors"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2.5 py-1 text-xs font-medium ${priorityTone(
                item.priority_score
              )}`}
            >
              Priority {Math.round(item.priority_score)}
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-white/50">
              {item.opportunity_type.replaceAll("_", " ")}
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-white/50">
              {item.urgency} urgency
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-white/50">
              {followUpStatusLabel}
            </span>
            <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${getLifecycleTone(lifecycleStatus)}`}>
              {lifecycleStatus.replaceAll("_", " ")}
            </span>
          </div>

          <h3 className="mt-3 text-base font-semibold text-white">{item.title}</h3>
          <p className="mt-2 text-sm text-white/60">{item.description}</p>
          <p className="mt-3 text-sm text-white/45">{item.recommended_action}</p>
          <p className="mt-2 text-xs text-white/35">{item.reason}</p>

          <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-white/40">
            <span>{formatDate(item.created_at)}</span>
            {contactName ? <span>{contactName}</span> : null}
            {relationshipScore !== null ? <ScoreBadge score={relationshipScore} size="sm" /> : null}
            <span>{Math.round(item.confidence * 100)}% confidence</span>
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {item.related_contact_id ? (
          <button
            onClick={() => onOpenContact(item.related_contact_id)}
            className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/70 hover:bg-white/10 hover:text-white transition-colors"
          >
            Open related contact
          </button>
        ) : null}

        <button
          onClick={() => onGenerate(item)}
          className="inline-flex items-center gap-2 rounded-xl border border-accent/25 bg-accent/12 px-3 py-2 text-sm font-medium text-accent hover:bg-accent/20 transition-colors"
        >
          <Sparkles className="h-4 w-4" />
          Generate prep
        </button>

        <button
          onClick={() => onAccept(item)}
          disabled={accepting}
          className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm transition-colors ${
            accepting
              ? "border-white/10 bg-white/5 text-white/35"
              : "border-emerald-500/20 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/15"
          }`}
        >
          <BadgeCheck className="h-4 w-4" />
          {accepting ? "Saving..." : "Accept"}
        </button>

        <button
          onClick={() => onConvert(item)}
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/70 hover:bg-white/10 hover:text-white transition-colors"
        >
          <Plus className="h-4 w-4" />
          Convert to follow-up
        </button>

        {item.related_follow_up_id ? (
          <button
            onClick={() => onComplete(item)}
            disabled={completing}
            className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm transition-colors ${
              completing
                ? "border-white/10 bg-white/5 text-white/35"
                : "border-emerald-500/20 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/15"
            }`}
          >
            <CheckCircle2 className="h-4 w-4" />
            {completing ? "Saving..." : "Mark completed"}
          </button>
        ) : null}

        <button
          onClick={() => onDismiss(item)}
          disabled={dismissing}
          className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm transition-colors ${
            dismissing
              ? "border-white/10 bg-white/5 text-white/35"
              : "border-red-500/20 bg-red-500/10 text-red-300 hover:bg-red-500/15"
          }`}
        >
          <MessageSquareX className="h-4 w-4" />
          {dismissing ? "Saving..." : "Dismiss"}
        </button>
      </div>
    </motion.div>
  );
}

export default function Opportunities() {
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [scores, setScores] = useState([]);
  const [followUps, setFollowUps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [contactFilter, setContactFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("priority_desc");
  const [acceptingId, setAcceptingId] = useState(null);
  const [dismissingId, setDismissingId] = useState(null);
  const [completingId, setCompletingId] = useState(null);
  const [followUpTarget, setFollowUpTarget] = useState(null);
  const [submittingFollowUp, setSubmittingFollowUp] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [opportunitiesData, contactsData, scoresData, followUpsData] = await Promise.all([
        api.opportunities.list(),
        api.contacts.list({ limit: 100, sort_by: "name", sort_order: "asc" }).catch(() => []),
        api.relationshipScores.list().catch(() => ({ scores: [] })),
        api.followUps.list({ limit: 100, sort_by: "due_date", sort_order: "asc" }).catch(() => []),
      ]);
      setOpportunities(opportunitiesData || []);
      setContacts(contactsData || []);
      setScores(scoresData?.scores || []);
      setFollowUps(followUpsData || []);
    } catch (err) {
      setError(err.message || "Failed to load opportunities.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const contactMap = useMemo(() => new Map(contacts.map((contact) => [contact.id, contact])), [contacts]);
  const scoreMap = useMemo(() => new Map(scores.map((score) => [score.contact_id, score])), [scores]);
  const followUpMap = useMemo(() => new Map(followUps.map((followUp) => [followUp.id, followUp])), [followUps]);

  const enrichedOpportunities = useMemo(
    () =>
      opportunities.map((item) => ({
        ...item,
        section: getOpportunitySection(item.opportunity_type),
        contactName: item.related_contact_id ? contactMap.get(item.related_contact_id)?.name || null : null,
        relationshipScore:
          item.related_contact_id && scoreMap.has(item.related_contact_id)
            ? scoreMap.get(item.related_contact_id).score
            : null,
        lifecycleStatus: item.lifecycle_status || "new",
        followUpStatusLabel: inferredStatus(item, followUpMap),
      })),
    [contactMap, followUpMap, opportunities, scoreMap]
  );

  const filteredOpportunities = useMemo(() => {
    let items = [...enrichedOpportunities];

    if (query.trim()) {
      const search = query.trim().toLowerCase();
      items = items.filter((item) =>
        [
          item.title,
          item.description,
          item.reason,
          item.recommended_action,
          item.contactName,
          item.opportunity_type,
        ]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(search))
      );
    }

    if (category) {
      items = items.filter((item) => item.section === category);
    }
    if (contactFilter) {
      items = items.filter((item) => String(item.related_contact_id || "") === contactFilter);
    }
    if (priorityFilter) {
      items = items.filter((item) => item.priority_score >= Number(priorityFilter));
    }
    if (statusFilter) {
      items = items.filter((item) =>
        [item.lifecycleStatus, item.followUpStatusLabel]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(statusFilter.toLowerCase()))
      );
    }

    items.sort((a, b) => {
      switch (sortBy) {
        case "priority_asc":
          return a.priority_score - b.priority_score;
        case "relationship_desc":
          return (b.relationshipScore ?? -1) - (a.relationshipScore ?? -1);
        case "created_desc":
          return new Date(b.created_at) - new Date(a.created_at);
        case "created_asc":
          return new Date(a.created_at) - new Date(b.created_at);
        case "opportunity_value":
          return b.priority_score - a.priority_score;
        case "priority_desc":
        default:
          return b.priority_score - a.priority_score;
      }
    });

    return items;
  }, [category, contactFilter, enrichedOpportunities, priorityFilter, query, sortBy, statusFilter]);

  const groupedSections = useMemo(
    () => ({
      "Priority opportunities": filteredOpportunities
        .filter((item) => !["dismissed", "completed"].includes(item.lifecycleStatus))
        .slice(0, 5),
      "Warm introductions": filteredOpportunities.filter((item) => item.section === "Warm introductions"),
      "Reconnection opportunities": filteredOpportunities.filter(
        (item) => item.section === "Reconnection opportunities"
      ),
      "Relationship growth opportunities": filteredOpportunities.filter(
        (item) => item.section === "Relationship growth opportunities"
      ),
      "Event-related opportunities": filteredOpportunities.filter(
        (item) => item.section === "Event-related opportunities"
      ),
    }),
    [filteredOpportunities]
  );

  async function handleAccept(item) {
    setAcceptingId(item.opportunity_id);
    try {
      await api.actionLifecycle.update({
        entity_kind: "opportunity",
        entity_id: item.opportunity_id,
        entity_type: item.opportunity_type,
        status: "accepted",
        notes: item.reason,
      });
      await loadData();
    } finally {
      setAcceptingId(null);
    }
  }

  async function handleDismiss(item) {
    setDismissingId(item.opportunity_id);
    try {
      await api.actionLifecycle.update({
        entity_kind: "opportunity",
        entity_id: item.opportunity_id,
        entity_type: item.opportunity_type,
        status: "dismissed",
        notes: item.reason,
      });
      await loadData();
    } finally {
      setDismissingId(null);
    }
  }

  async function handleComplete(item) {
    setCompletingId(item.opportunity_id);
    try {
      if (item.related_follow_up_id) {
        const followUp = followUpMap.get(item.related_follow_up_id);
        if (followUp) {
          await api.followUps.update(item.related_follow_up_id, {
            title: followUp.title,
            description: followUp.description,
            due_date: followUp.due_date,
            contact_id: followUp.contact_id,
            event_id: followUp.event_id,
            status: "completed",
          });
        }
      }
      await api.actionLifecycle.update({
        entity_kind: "opportunity",
        entity_id: item.opportunity_id,
        entity_type: item.opportunity_type,
        status: "completed",
        notes: item.reason,
      });
      await loadData();
    } finally {
      setCompletingId(null);
    }
  }

  function handleGenerate(item) {
    navigate("/generate", {
      state: {
        prefill: {
          description: `${item.title}. ${item.description} ${item.recommended_action}`.trim(),
          interests: item.contactName || "",
          sourceType: "opportunity",
          sourceTitle: item.title,
          contactName: item.contactName,
          opportunity: {
            id: item.opportunity_id,
            title: item.title,
            type: item.opportunity_type,
            recommendedAction: item.recommended_action,
          },
        },
      },
    });
  }

  async function handleConvertToFollowUp(payload) {
    setSubmittingFollowUp(true);
    try {
      const created = await api.followUps.create(payload);
      await api.actionLifecycle.update({
        entity_kind: "opportunity",
        entity_id: followUpTarget.opportunity_id,
        entity_type: followUpTarget.opportunity_type,
        status: "converted_to_follow_up",
        converted_follow_up_id: created.id,
        notes: followUpTarget.reason,
      });
      setFollowUpTarget(null);
      await loadData();
    } finally {
      setSubmittingFollowUp(false);
    }
  }

  const categoryOptions = [
    "Warm introductions",
    "Reconnection opportunities",
    "Relationship growth opportunities",
    "Event-related opportunities",
    "Priority opportunities",
  ];

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
        <ErrorState message={error} onRetry={loadData} />
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
            <Target className="h-5 w-5 text-accent" />
            <h1 className="text-2xl font-semibold text-white">Opportunities</h1>
          </div>
          <p className="mt-2 text-sm text-white/50">
            Strategic opportunities derived from relationship scores, bridge signals, events, and overdue actions.
          </p>
        </div>
      </section>

      <section className="glass rounded-2xl p-4 lg:p-5 space-y-4">
        <div className="grid gap-3 lg:grid-cols-[1.6fr_1fr_1fr_1fr_1fr]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/30" />
            <input
              type="text"
              placeholder="Search opportunities"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
            />
          </div>

          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white focus:outline-none focus:border-accent/50"
          >
            <option value="">All categories</option>
            {categoryOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>

          <select
            value={contactFilter}
            onChange={(event) => setContactFilter(event.target.value)}
            className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white focus:outline-none focus:border-accent/50"
          >
            <option value="">All contacts</option>
            {contacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name}
              </option>
            ))}
          </select>

          <select
            value={priorityFilter}
            onChange={(event) => setPriorityFilter(event.target.value)}
            className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white focus:outline-none focus:border-accent/50"
          >
            <option value="">All priorities</option>
            <option value="85">85+</option>
            <option value="70">70+</option>
            <option value="50">50+</option>
          </select>

          <label className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white/70">
            <ArrowUpDown className="h-4 w-4 text-white/35" />
            <select
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value)}
              className="w-full bg-transparent text-sm text-white focus:outline-none"
            >
              <option value="priority_desc">Priority high-low</option>
              <option value="priority_asc">Priority low-high</option>
              <option value="relationship_desc">Relationship score</option>
              <option value="opportunity_value">Opportunity value</option>
              <option value="created_desc">Newest first</option>
              <option value="created_asc">Oldest first</option>
            </select>
          </label>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white focus:outline-none focus:border-accent/50"
          >
            <option value="">All statuses</option>
            <option value="accepted">Accepted</option>
            <option value="dismissed">Dismissed</option>
            <option value="completed">Completed</option>
            <option value="converted_to_follow_up">Converted to follow-up</option>
            <option value="completed">Completed follow-up</option>
            <option value="pending">Pending follow-up</option>
            <option value="No linked follow-up">No linked follow-up</option>
          </select>
          <div className="flex flex-wrap items-center gap-3 text-xs text-white/45">
            <span>{filteredOpportunities.length} opportunities</span>
            <span className="text-white/20">•</span>
            <span>{filteredOpportunities.filter((item) => item.related_event_id).length} event-related</span>
            <span className="text-white/20">•</span>
            <span>{filteredOpportunities.filter((item) => item.related_contact_id).length} contact-linked</span>
          </div>
        </div>
      </section>

      {filteredOpportunities.length === 0 ? (
        <div className="glass rounded-2xl">
          <EmptyState
            icon={Target}
            title="No opportunities match this view"
            description="Try clearing a filter or add more relationship data so the backend can surface opportunity signals."
            actionLabel="Clear filters"
            onAction={() => {
              setQuery("");
              setCategory("");
              setContactFilter("");
              setPriorityFilter("");
              setStatusFilter("");
              setSortBy("priority_desc");
            }}
          />
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedSections).map(([sectionTitle, items]) => (
            <section key={sectionTitle} className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium uppercase tracking-wide text-white/55">{sectionTitle}</h2>
                <span className="text-xs text-white/35">{items.length}</span>
              </div>
              {items.length === 0 ? (
                <div className="glass rounded-2xl">
                  <EmptyState
                    icon={Users2}
                    title={`No ${sectionTitle.toLowerCase()}`}
                    description="The backend did not return items for this category under the current filters."
                  />
                </div>
              ) : (
                <div className="grid gap-4 xl:grid-cols-2">
                  {items.map((item) => (
                    <OpportunityCard
                      key={item.opportunity_id}
                      item={item}
                      contactName={item.contactName}
                      relationshipScore={item.relationshipScore}
                      lifecycleStatus={item.lifecycleStatus}
                      followUpStatusLabel={item.followUpStatusLabel}
                      onAccept={handleAccept}
                      onOpenContact={(contactId) => navigate(`/contacts/${contactId}`)}
                      onDismiss={handleDismiss}
                      onComplete={handleComplete}
                      onConvert={setFollowUpTarget}
                      onGenerate={handleGenerate}
                      accepting={acceptingId === item.opportunity_id}
                      dismissing={dismissingId === item.opportunity_id}
                      completing={completingId === item.opportunity_id}
                    />
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      )}

      <section className="glass rounded-2xl p-5 lg:p-6">
        <div className="flex items-center gap-2 mb-3">
          <CalendarClock className="h-4 w-4 text-accent" />
          <h2 className="text-base font-semibold text-white">Backend limitations</h2>
        </div>
        <p className="text-sm text-white/55 max-w-3xl">
          Opportunity lifecycle now uses the backend action lifecycle API. Follow-up conversion still uses the
          existing create-follow-up flow first, then updates lifecycle state separately because there is no atomic
          backend conversion endpoint yet.
        </p>
      </section>

      <Modal open={Boolean(followUpTarget)} onClose={() => setFollowUpTarget(null)} title="Convert to follow-up">
        {followUpTarget && (
          <FollowUpForm
            contactId={followUpTarget.related_contact_id || undefined}
            eventId={followUpTarget.related_event_id || undefined}
            initialValues={{
              title: followUpTarget.title,
              description: `${followUpTarget.description}\n\nAction: ${followUpTarget.recommended_action}`.trim(),
            }}
            onSubmit={handleConvertToFollowUp}
            onCancel={() => setFollowUpTarget(null)}
            submitting={submittingFollowUp}
          />
        )}
      </Modal>
    </motion.div>
  );
}
