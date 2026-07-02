import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  CalendarClock,
  Handshake,
  ListChecks,
  Network,
  Sparkles,
  TrendingUp,
  Users2,
} from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import ScoreBadge from "../components/ui/ScoreBadge";
import StatCard from "../components/ui/StatCard";
import { SkeletonCard, SkeletonLine } from "../components/ui/SkeletonLoader";
import { useOnboardingStatus } from "../hooks/useOnboardingStatus";

const CLOSED_FOLLOW_UP_STATUSES = new Set(["done", "completed", "complete", "closed"]);
const HIDDEN_LIFECYCLE_STATUSES = new Set(["dismissed", "completed"]);

function useDashboardSection(loader) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSection = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await loader();
      setData(result);
    } catch (err) {
      setError(err.message || "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, [loader]);

  useEffect(() => {
    fetchSection();
  }, [fetchSection]);

  return { data, loading, error, refetch: fetchSection };
}

function formatDate(value, options = { month: "short", day: "numeric" }) {
  if (!value) return null;
  return new Intl.DateTimeFormat(undefined, options).format(new Date(value));
}

function formatDecimal(value, digits = 1) {
  return Number(value || 0).toFixed(digits);
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0))}`;
}

function getDueLabel(dueDate) {
  if (!dueDate) return "No due date";

  const now = new Date();
  const due = new Date(dueDate);
  const diffMs = due.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) {
    return `${Math.abs(diffDays)}d overdue`;
  }
  if (diffDays === 0) {
    return "Due today";
  }
  if (diffDays === 1) {
    return "Due tomorrow";
  }
  return `Due in ${diffDays}d`;
}

function getPriorityTone(score) {
  if (score >= 85) return "text-red-300 bg-red-500/10 border-red-500/20";
  if (score >= 70) return "text-amber-300 bg-amber-500/10 border-amber-500/20";
  return "text-emerald-300 bg-emerald-500/10 border-emerald-500/20";
}

function openEntityFromInsight(navigate, item) {
  if (item.related_contact_id) {
    navigate(`/contacts/${item.related_contact_id}`);
    return;
  }
  if (item.related_event_id) {
    navigate("/events");
    return;
  }
  if (item.related_follow_up_id) {
    navigate("/follow-ups");
  }
}

function DashboardSection({ title, subtitle, icon: Icon, actionLabel, onAction, children }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28 }}
      className="glass rounded-2xl p-5 lg:p-6"
    >
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white/5 border border-white/8">
              <Icon className="h-4 w-4 text-accent" />
            </span>
            <div>
              <h2 className="text-base font-semibold text-white">{title}</h2>
              {subtitle && <p className="text-sm text-white/45 mt-0.5">{subtitle}</p>}
            </div>
          </div>
        </div>
        {actionLabel && onAction && (
          <button
            onClick={onAction}
            className="inline-flex items-center gap-1.5 text-sm text-white/55 hover:text-white transition-colors"
          >
            {actionLabel}
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      {children}
    </motion.section>
  );
}

function SectionSkeleton({ rows = 4 }) {
  return (
    <div className="glass rounded-2xl p-5 lg:p-6 space-y-4">
      <div className="space-y-2">
        <SkeletonLine width="32%" height="1rem" />
        <SkeletonLine width="50%" height="0.875rem" />
      </div>
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, index) => (
          <div key={index} className="rounded-xl border border-white/6 bg-white/[0.03] p-4 space-y-2">
            <SkeletonLine width="45%" height="0.9rem" />
            <SkeletonLine width="80%" height="0.8rem" />
            <SkeletonLine width="60%" height="0.8rem" />
          </div>
        ))}
      </div>
    </div>
  );
}

function InsightRow({ title, description, meta, badge, onClick }) {
  const Wrapper = onClick ? "button" : "div";

  return (
    <Wrapper
      onClick={onClick}
      className={`w-full text-left rounded-xl border border-white/6 bg-white/[0.03] px-4 py-3 transition-colors ${
        onClick ? "hover:bg-white/[0.06]" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-white truncate">{title}</p>
          {description && <p className="text-sm text-white/55 mt-1 line-clamp-2">{description}</p>}
          {meta && <p className="text-xs text-white/35 mt-2">{meta}</p>}
        </div>
        {badge}
      </div>
    </Wrapper>
  );
}

function DashboardStats({ analytics, loading, error, onRetry, onViewContacts, onViewFollowUps }) {
  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <SkeletonCard key={index} />
        ))}
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />;
  }

  const cards = [
    {
      label: "Contacts",
      value: analytics.total_contacts,
      icon: Users2,
      onClick: onViewContacts,
    },
    {
      label: "Events",
      value: analytics.total_events,
      icon: CalendarClock,
    },
    {
      label: "Overdue follow-ups",
      value: analytics.overdue_follow_ups_count,
      icon: AlertCircle,
      onClick: onViewFollowUps,
    },
    {
      label: "Cold contacts",
      value: analytics.cold_contacts_count,
      icon: Handshake,
      onClick: onViewContacts,
    },
    {
      label: "Network health",
      value: `${formatPercent(analytics.network_health_score)}%`,
      icon: TrendingUp,
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {cards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </div>

      <div className="glass rounded-2xl p-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-3 text-sm text-white/60">
          <span>Avg. strength: <span className="text-white">{formatDecimal(analytics.average_relationship_strength)}</span></span>
          <span className="hidden lg:inline text-white/15">•</span>
          <span>Interaction frequency: <span className="text-white">{formatDecimal(analytics.interaction_frequency)}</span></span>
          <span className="hidden lg:inline text-white/15">•</span>
          <span>Upcoming follow-ups: <span className="text-white">{analytics.upcoming_follow_ups_count}</span></span>
        </div>
        <div className="flex flex-wrap gap-2">
          {analytics.top_relationship_tags.length > 0 ? (
            analytics.top_relationship_tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/60"
              >
                {tag}
              </span>
            ))
          ) : (
            <span className="text-xs text-white/35">No relationship tags yet.</span>
          )}
        </div>
      </div>
    </div>
  );
}

function Dashboard() {
  const navigate = useNavigate();
  const { username } = useAuth();
  const onboarding = useOnboardingStatus(username);

  const analyticsSection = useDashboardSection(
    useCallback(() => api.analytics.summary(), [])
  );
  const recommendationsSection = useDashboardSection(
    useCallback(() => api.recommendations.nextBestActions(4), [])
  );
  const opportunitiesSection = useDashboardSection(
    useCallback(() => api.opportunities.list(), [])
  );
  const followUpsSection = useDashboardSection(
    useCallback(
      () =>
        api.followUps.list({
          sort_by: "due_date",
          sort_order: "asc",
          limit: 20,
        }),
      []
    )
  );
  const relationshipScoresSection = useDashboardSection(
    useCallback(() => api.relationshipScores.list(), [])
  );
  const networkSection = useDashboardSection(
    useCallback(() => api.network.graphInsights(), [])
  );

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  const recommendations = (recommendationsSection.data || []).filter(
    (item) => !HIDDEN_LIFECYCLE_STATUSES.has((item.lifecycle_status || "new").toLowerCase())
  );
  const opportunities = (opportunitiesSection.data || [])
    .filter((item) => !HIDDEN_LIFECYCLE_STATUSES.has((item.lifecycle_status || "new").toLowerCase()))
    .slice(0, 4);
  const relationshipScores = relationshipScoresSection.data?.scores || [];
  const network = networkSection.data;

  const urgentFollowUps = (followUpsSection.data || [])
    .filter((item) => !CLOSED_FOLLOW_UP_STATUSES.has((item.status || "").toLowerCase()))
    .filter((item) => item.due_date)
    .sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime())
    .slice(0, 5);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6"
    >
      <section className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-white/30">Command Center</p>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white mt-2">
            {greeting}{username ? `, ${username}` : ""}
          </h1>
          <p className="text-sm sm:text-base text-white/55 mt-2 max-w-2xl">
            Real-time relationship intelligence from your analytics, recommendations, opportunities,
            follow-ups, scores, and network graph.
          </p>
        </div>
      </section>

      {!onboarding.loading && onboarding.needsOnboarding ? (
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.24 }}
          className="glass rounded-2xl p-5 lg:p-6"
        >
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-sm font-semibold text-white">Complete your first-time setup</p>
              <p className="mt-1 text-sm text-white/55">
                Your dashboard is using real backend data. Add the missing profile, contact, and first event or
                follow-up records to unlock a fuller experience.
              </p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-white/45">
                <span className={`rounded-full px-3 py-1 ${onboarding.profileComplete ? "bg-emerald-500/15 text-emerald-200" : "bg-white/5"}`}>
                  {onboarding.profileComplete ? "Profile ready" : "Profile needed"}
                </span>
                <span className={`rounded-full px-3 py-1 ${onboarding.hasContacts ? "bg-emerald-500/15 text-emerald-200" : "bg-white/5"}`}>
                  {onboarding.hasContacts ? "Contact added" : "First contact needed"}
                </span>
                <span className={`rounded-full px-3 py-1 ${onboarding.hasActivity ? "bg-emerald-500/15 text-emerald-200" : "bg-white/5"}`}>
                  {onboarding.hasActivity ? "Workflow active" : "Event or follow-up needed"}
                </span>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => navigate("/onboarding")}
                className="rounded-xl bg-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent/90"
              >
                {onboarding.preference.status === "skipped" ? "Resume onboarding" : "Open onboarding"}
              </button>
            </div>
          </div>
        </motion.section>
      ) : null}

      <DashboardStats
        analytics={analyticsSection.data}
        loading={analyticsSection.loading}
        error={analyticsSection.error}
        onRetry={analyticsSection.refetch}
        onViewContacts={() => navigate("/contacts")}
        onViewFollowUps={() => navigate("/follow-ups")}
      />

      <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
        {recommendationsSection.loading ? (
          <SectionSkeleton />
        ) : recommendationsSection.error ? (
          <ErrorState message={recommendationsSection.error} onRetry={recommendationsSection.refetch} />
        ) : (
          <DashboardSection
            title="Next Best Actions"
            subtitle="Highest-priority recommendation signals from the backend."
            icon={Sparkles}
            actionLabel="Contacts"
            onAction={() => navigate("/contacts")}
          >
            {recommendations.length === 0 ? (
              <EmptyState
                title="No actions yet"
                description="Add contacts, interactions, and follow-ups to unlock personalized next steps."
                actionLabel="Add contacts"
                onAction={() => navigate("/contacts")}
              />
            ) : (
              <div className="space-y-3">
                {recommendations.map((item) => (
                  <motion.div
                    key={item.recommendation_id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <InsightRow
                      title={item.title}
                      description={item.description}
                      meta={item.reason}
                      onClick={() => openEntityFromInsight(navigate, item)}
                      badge={
                        <span
                          className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium ${getPriorityTone(
                            item.priority_score
                          )}`}
                        >
                          {formatDecimal(item.priority_score, 0)}
                        </span>
                      }
                    />
                  </motion.div>
                ))}
              </div>
            )}
          </DashboardSection>
        )}

        {followUpsSection.loading ? (
          <SectionSkeleton rows={3} />
        ) : followUpsSection.error ? (
          <ErrorState message={followUpsSection.error} onRetry={followUpsSection.refetch} />
        ) : (
          <DashboardSection
            title="Urgent Follow-Ups"
            subtitle="Open items with the nearest due dates."
            icon={ListChecks}
            actionLabel="Follow-ups"
            onAction={() => navigate("/follow-ups")}
          >
            {urgentFollowUps.length === 0 ? (
              <EmptyState
                icon={ListChecks}
                title="No urgent follow-ups"
                description="Nothing active is due right now. New follow-ups will surface here automatically."
              />
            ) : (
              <div className="space-y-3">
                {urgentFollowUps.map((item) => (
                  <InsightRow
                    key={item.id}
                    title={item.title}
                    description={item.description || item.status}
                    meta={`${getDueLabel(item.due_date)} • ${formatDate(item.due_date, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}`}
                    onClick={() =>
                      item.contact_id ? navigate(`/contacts/${item.contact_id}`) : navigate("/follow-ups")
                    }
                    badge={
                      <span className="shrink-0 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-white/65">
                        {item.status}
                      </span>
                    }
                  />
                ))}
              </div>
            )}
          </DashboardSection>
        )}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        {opportunitiesSection.loading ? (
          <SectionSkeleton />
        ) : opportunitiesSection.error ? (
          <ErrorState message={opportunitiesSection.error} onRetry={opportunitiesSection.refetch} />
        ) : (
          <DashboardSection
            title="Opportunity Feed"
            subtitle="Time-sensitive openings detected from events, follow-ups, and relationship signals."
            icon={CalendarClock}
          >
            {opportunities.length === 0 ? (
              <EmptyState
                title="No active opportunities"
                description="As you log more relationship activity, timely opportunities will show up here."
              />
            ) : (
              <div className="space-y-3">
                {opportunities.map((item) => (
                  <InsightRow
                    key={item.opportunity_id}
                    title={item.title}
                    description={item.recommended_action}
                    meta={`${item.reason} • ${item.urgency} urgency • ${formatDecimal(item.confidence * 100, 0)}% confidence`}
                    onClick={() => openEntityFromInsight(navigate, item)}
                    badge={
                      <span
                        className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium ${getPriorityTone(
                          item.priority_score
                        )}`}
                      >
                        {formatDecimal(item.priority_score, 0)}
                      </span>
                    }
                  />
                ))}
              </div>
            )}
          </DashboardSection>
        )}

        {relationshipScoresSection.loading ? (
          <SectionSkeleton rows={4} />
        ) : relationshipScoresSection.error ? (
          <ErrorState message={relationshipScoresSection.error} onRetry={relationshipScoresSection.refetch} />
        ) : (
          <DashboardSection
            title="Top Relationship Scores"
            subtitle="Highest-value contacts ranked by explainable scoring."
            icon={TrendingUp}
            actionLabel="Contacts"
            onAction={() => navigate("/contacts")}
          >
            {relationshipScores.length === 0 ? (
              <EmptyState
                icon={Users2}
                title="No scored relationships"
                description="Relationship scores appear once contacts and interactions exist."
                actionLabel="Add contacts"
                onAction={() => navigate("/contacts")}
              />
            ) : (
              <div className="space-y-3">
                {relationshipScores.slice(0, 5).map((item) => (
                  <button
                    key={item.contact_id}
                    onClick={() => navigate(`/contacts/${item.contact_id}`)}
                    className="w-full text-left rounded-xl border border-white/6 bg-white/[0.03] px-4 py-3 hover:bg-white/[0.06] transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-white truncate">{item.name}</p>
                        <p className="text-xs text-white/45 mt-1">
                          {item.relationship_strength} strength • {item.relationship_risk} risk
                        </p>
                        <p className="text-xs text-white/35 mt-2">
                          Graph {formatDecimal(item.factors.graph_score, 0)} • Recency {formatDecimal(item.factors.recency_score, 0)}
                        </p>
                      </div>
                      <ScoreBadge score={item.score} size="sm" />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </DashboardSection>
        )}
      </div>

      {networkSection.loading ? (
        <SectionSkeleton rows={3} />
      ) : networkSection.error ? (
        <ErrorState message={networkSection.error} onRetry={networkSection.refetch} />
      ) : (
        <DashboardSection
          title="Network Snapshot"
          subtitle="Graph-level signal on bridges, clusters, and tie strength."
          icon={Network}
          actionLabel="Events"
          onAction={() => navigate("/events")}
        >
          {!network || network.total_contacts === 0 ? (
            <EmptyState
              icon={Network}
              title="No network graph yet"
              description="Add contacts plus a few interactions or events to unlock graph insights."
            />
          ) : (
            <div className="space-y-5">
              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-xl border border-white/6 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-wide text-white/35">Contacts</p>
                  <p className="text-2xl font-semibold text-white mt-2">{network.total_contacts}</p>
                </div>
                <div className="rounded-xl border border-white/6 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-wide text-white/35">Density</p>
                  <p className="text-2xl font-semibold text-white mt-2">
                    {formatDecimal(network.network_density_estimate, 2)}
                  </p>
                </div>
                <div className="rounded-xl border border-white/6 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-wide text-white/35">Bridge contacts</p>
                  <p className="text-2xl font-semibold text-white mt-2">{network.bridge_contacts.length}</p>
                </div>
                <div className="rounded-xl border border-white/6 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-wide text-white/35">Clusters</p>
                  <p className="text-2xl font-semibold text-white mt-2">{network.clusters.length}</p>
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <div className="rounded-xl border border-white/6 bg-white/[0.03] p-4">
                  <p className="text-sm font-medium text-white">Strong ties</p>
                  <div className="mt-3 space-y-2">
                    {network.strong_tie_contacts.slice(0, 3).map((item) => (
                      <button
                        key={`strong-${item.contact_id}`}
                        onClick={() => navigate(`/contacts/${item.contact_id}`)}
                        className="block w-full text-left text-sm text-white/70 hover:text-white transition-colors"
                      >
                        {item.name}
                      </button>
                    ))}
                    {network.strong_tie_contacts.length === 0 && (
                      <p className="text-sm text-white/35">No strong ties detected yet.</p>
                    )}
                  </div>
                </div>

                <div className="rounded-xl border border-white/6 bg-white/[0.03] p-4">
                  <p className="text-sm font-medium text-white">Bridge contacts</p>
                  <div className="mt-3 space-y-2">
                    {network.bridge_contacts.slice(0, 3).map((item) => (
                      <button
                        key={`bridge-${item.contact_id}`}
                        onClick={() => navigate(`/contacts/${item.contact_id}`)}
                        className="block w-full text-left text-sm text-white/70 hover:text-white transition-colors"
                      >
                        {item.name}
                      </button>
                    ))}
                    {network.bridge_contacts.length === 0 && (
                      <p className="text-sm text-white/35">No bridge contacts surfaced yet.</p>
                    )}
                  </div>
                </div>

                <div className="rounded-xl border border-white/6 bg-white/[0.03] p-4">
                  <p className="text-sm font-medium text-white">Weak ties</p>
                  <div className="mt-3 space-y-2">
                    {network.weak_tie_candidates.slice(0, 3).map((item) => (
                      <button
                        key={`weak-${item.contact_id}`}
                        onClick={() => navigate(`/contacts/${item.contact_id}`)}
                        className="block w-full text-left text-sm text-white/70 hover:text-white transition-colors"
                      >
                        {item.name}
                      </button>
                    ))}
                    {network.weak_tie_candidates.length === 0 && (
                      <p className="text-sm text-white/35">No weak-tie candidates yet.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </DashboardSection>
      )}
    </motion.div>
  );
}

export default Dashboard;
