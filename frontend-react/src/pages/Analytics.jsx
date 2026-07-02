import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowUpDown,
  BarChart3,
  CalendarClock,
  CheckCircle2,
  Filter,
  Lightbulb,
  Plus,
  Search,
  Sparkles,
  TrendingUp,
  Users2,
} from "lucide-react";
import { api } from "../api/client";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import Modal from "../components/ui/Modal";
import FollowUpForm from "../components/domain/FollowUpForm";
import ScoreBadge from "../components/ui/ScoreBadge";
import StatCard from "../components/ui/StatCard";
import { SkeletonCard } from "../components/ui/SkeletonLoader";
import { DonutChart, MiniBarChart, MiniLineChart } from "../components/ui/SimpleCharts";

function monthLabel(dateString) {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat(undefined, { month: "short" }).format(date);
}

function withinRange(dateString, range) {
  if (!dateString || range === "all") return true;
  const date = new Date(dateString);
  const now = new Date();
  const cutoff =
    range === "30d"
      ? new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
      : new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
  return date >= cutoff;
}

function relationshipBucket(item) {
  return item.relationship_strength;
}

function activityBucket(count) {
  if (count >= 5) return "high";
  if (count >= 2) return "medium";
  return "low";
}

function scoreRangeLabel(score) {
  if (score >= 80) return "80-100";
  if (score >= 60) return "60-79";
  if (score >= 40) return "40-59";
  return "0-39";
}

function InsightCard({ title, subtitle, icon: Icon, children }) {
  return (
    <section className="glass rounded-2xl p-5 lg:p-6">
      <div className="mb-4 flex items-center gap-2">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-white/8 bg-white/5">
          <Icon className="h-4 w-4 text-accent" />
        </span>
        <div>
          <h2 className="text-base font-semibold text-white">{title}</h2>
          {subtitle ? <p className="text-sm text-white/45">{subtitle}</p> : null}
        </div>
      </div>
      {children}
    </section>
  );
}

export default function Analytics() {
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [scores, setScores] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [interactions, setInteractions] = useState([]);
  const [followUps, setFollowUps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dateRange, setDateRange] = useState("all");
  const [relationshipCategory, setRelationshipCategory] = useState("");
  const [scoreRange, setScoreRange] = useState("");
  const [activityLevel, setActivityLevel] = useState("");
  const [sortBy, setSortBy] = useState("score_desc");
  const [query, setQuery] = useState("");
  const [followUpTarget, setFollowUpTarget] = useState(null);
  const [submittingFollowUp, setSubmittingFollowUp] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [analyticsData, metricsData, scoresData, contactsData, interactionsData, followUpsData] = await Promise.all([
        api.analytics.summary(),
        api.metrics.get(),
        api.relationshipScores.list(),
        api.contacts.list({ limit: 100, sort_by: "name", sort_order: "asc" }).catch(() => []),
        api.interactions.list({ limit: 100, sort_order: "desc" }).catch(() => []),
        api.followUps.list({ limit: 100, sort_by: "due_date", sort_order: "asc" }).catch(() => []),
      ]);
      setAnalytics(analyticsData);
      setMetrics(metricsData);
      setScores(scoresData?.scores || []);
      setContacts(contactsData || []);
      setInteractions(interactionsData || []);
      setFollowUps(followUpsData || []);
    } catch (err) {
      setError(err.message || "Failed to load analytics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const interactionSummary = useMemo(() => {
    const monthly = new Map();
    const perContact = new Map();

    for (const interaction of interactions) {
      if (!withinRange(interaction.created_at, dateRange)) continue;
      const label = monthLabel(interaction.created_at);
      monthly.set(label, (monthly.get(label) || 0) + 1);

      if (!interaction.contact_id) continue;
      perContact.set(interaction.contact_id, (perContact.get(interaction.contact_id) || 0) + 1);
    }

    return { monthly, perContact };
  }, [dateRange, interactions]);

  const filteredScores = useMemo(() => {
    const contactMap = new Map(contacts.map((contact) => [contact.id, contact]));
    let items = scores.map((item) => ({
      ...item,
      contact: contactMap.get(item.contact_id) || null,
      activityLevel: activityBucket(interactionSummary.perContact.get(item.contact_id) || 0),
      scoreBucket: scoreRangeLabel(item.score),
    }));

    if (query.trim()) {
      const search = query.trim().toLowerCase();
      items = items.filter((item) =>
        [item.name, item.contact?.company, item.contact?.role].filter(Boolean).some((value) => value.toLowerCase().includes(search))
      );
    }
    if (relationshipCategory) {
      items = items.filter(
        (item) =>
          relationshipBucket(item) === relationshipCategory ||
          item.relationship_risk === relationshipCategory
      );
    }
    if (scoreRange) {
      items = items.filter((item) => item.scoreBucket === scoreRange);
    }
    if (activityLevel) {
      items = items.filter((item) => item.activityLevel === activityLevel);
    }

    items.sort((a, b) => {
      switch (sortBy) {
        case "recent_activity":
          return (interactionSummary.perContact.get(b.contact_id) || 0) - (interactionSummary.perContact.get(a.contact_id) || 0);
        case "opportunity_count":
          return (b.factors.recommendation_score || 0) - (a.factors.recommendation_score || 0);
        case "score_asc":
          return a.score - b.score;
        case "trend_direction":
          return (b.factors.recency_score || 0) - (a.factors.recency_score || 0);
        case "score_desc":
        default:
          return b.score - a.score;
      }
    });

    return items;
  }, [activityLevel, contacts, interactionSummary.perContact, query, relationshipCategory, scoreRange, scores, sortBy]);

  const interactionTrendData = useMemo(() => {
    return Array.from(interactionSummary.monthly.entries()).map(([label, value]) => ({ label, value }));
  }, [interactionSummary.monthly]);

  const relationshipDistribution = useMemo(() => {
    const categories = ["weak", "developing", "healthy", "strong", "strategic"];
    return categories.map((label) => ({
      label,
      value: filteredScores.filter((item) => item.relationship_strength === label).length,
    }));
  }, [filteredScores]);

  const scoreDistribution = useMemo(() => {
    const buckets = ["80-100", "60-79", "40-59", "0-39"];
    return buckets.map((label) => ({
      label,
      value: filteredScores.filter((item) => item.scoreBucket === label).length,
    }));
  }, [filteredScores]);

  const topRelationships = filteredScores.slice(0, 5);
  const recommendationEffectivenessSegments = metrics?.user_effectiveness
    ? [
        {
          label: "Accepted",
          value: metrics.user_effectiveness.recommendations.acceptance_rate,
          color: "#22c55e",
        },
        {
          label: "Rejected",
          value: metrics.user_effectiveness.recommendations.rejection_rate,
          color: "#ef4444",
        },
      ]
    : [];

  const followUpStateSegments = analytics
    ? [
        { label: "Completed", value: analytics.completed_follow_ups_count, color: "#22c55e" },
        { label: "Overdue", value: analytics.overdue_follow_ups_count, color: "#ef4444" },
        { label: "Upcoming", value: analytics.upcoming_follow_ups_count, color: "#f59e0b" },
      ]
    : [];

  async function handleCreateFollowUp(payload) {
    setSubmittingFollowUp(true);
    try {
      await api.followUps.create(payload);
      setFollowUpTarget(null);
    } finally {
      setSubmittingFollowUp(false);
    }
  }

  function handleGenerate(item) {
    navigate("/generate", {
      state: {
        prefill: {
          description: `${item.name}${item.contact?.company ? ` at ${item.contact.company}` : ""}${item.contact?.notes ? ` - ${item.contact.notes}` : ""}`,
          interests: Array.isArray(item.contact?.tags) ? item.contact.tags.join(", ") : "",
        },
      },
    });
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
            <BarChart3 className="h-5 w-5 text-accent" />
            <h1 className="text-2xl font-semibold text-white">Analytics</h1>
          </div>
          <p className="mt-2 text-sm text-white/50">
            Network health, relationship distribution, interaction activity, and effectiveness metrics from the live backend.
          </p>
        </div>
      </section>

      <section className="glass rounded-2xl p-4 lg:p-5 space-y-4">
        <div className="grid gap-3 lg:grid-cols-[1.3fr_1fr_1fr_1fr_1fr]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/30" />
            <input
              type="text"
              placeholder="Search by relationship"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
            />
          </div>

          <select
            value={dateRange}
            onChange={(event) => setDateRange(event.target.value)}
            className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white focus:outline-none focus:border-accent/50"
          >
            <option value="all">All time</option>
            <option value="30d">Last 30d</option>
            <option value="90d">Last 90d</option>
          </select>

          <label className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white/70">
            <Filter className="h-4 w-4 text-white/35" />
            <select
              value={relationshipCategory}
              onChange={(event) => setRelationshipCategory(event.target.value)}
              className="w-full bg-transparent text-sm text-white focus:outline-none"
            >
              <option value="">All relationship categories</option>
              <option value="weak">Weak</option>
              <option value="developing">Developing</option>
              <option value="healthy">Healthy</option>
              <option value="strong">Strong</option>
              <option value="strategic">Strategic</option>
              <option value="high">High risk</option>
              <option value="medium">Medium risk</option>
              <option value="low">Low risk</option>
            </select>
          </label>

          <select
            value={scoreRange}
            onChange={(event) => setScoreRange(event.target.value)}
            className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white focus:outline-none focus:border-accent/50"
          >
            <option value="">All score ranges</option>
            <option value="80-100">80-100</option>
            <option value="60-79">60-79</option>
            <option value="40-59">40-59</option>
            <option value="0-39">0-39</option>
          </select>

          <div className="grid gap-2 sm:grid-cols-2">
            <select
              value={activityLevel}
              onChange={(event) => setActivityLevel(event.target.value)}
              className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white focus:outline-none focus:border-accent/50"
            >
              <option value="">All activity levels</option>
              <option value="high">High activity</option>
              <option value="medium">Medium activity</option>
              <option value="low">Low activity</option>
            </select>
            <label className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white/70">
              <ArrowUpDown className="h-4 w-4 text-white/35" />
              <select
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value)}
                className="w-full bg-transparent text-sm text-white focus:outline-none"
              >
                <option value="score_desc">Score</option>
                <option value="score_asc">Score low-high</option>
                <option value="trend_direction">Trend direction</option>
                <option value="recent_activity">Recent activity</option>
                <option value="opportunity_count">Opportunity count</option>
              </select>
            </label>
          </div>
        </div>
      </section>

      {analytics && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Network health" value={`${Math.round(analytics.network_health_score)}%`} icon={TrendingUp} />
          <StatCard label="Contacts" value={analytics.total_contacts} icon={Users2} />
          <StatCard label="Interactions" value={analytics.total_interactions} icon={CalendarClock} />
          <StatCard label="Follow-ups" value={analytics.total_follow_ups} icon={CheckCircle2} />
          <StatCard label="Cold contacts" value={analytics.cold_contacts_count} icon={Lightbulb} />
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <InsightCard title="Network health overview" subtitle="High-level health and relationship concentration." icon={TrendingUp}>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
              <p className="text-xs uppercase tracking-wide text-white/35">Top tags</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {analytics?.top_relationship_tags?.length ? analytics.top_relationship_tags.map((tag) => (
                  <span key={tag} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/60">
                    {tag}
                  </span>
                )) : <p className="text-sm text-white/35">No relationship tags available.</p>}
              </div>
            </div>
            <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
              <p className="text-xs uppercase tracking-wide text-white/35">Relationship score distribution</p>
              <div className="mt-3">
                <MiniBarChart data={scoreDistribution} />
              </div>
            </div>
          </div>
        </InsightCard>

        <InsightCard title="Relationship distribution metrics" subtitle="Distribution by strength buckets from real score output." icon={Users2}>
          <MiniBarChart data={relationshipDistribution} />
        </InsightCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <InsightCard title="Interaction activity trends" subtitle="Monthly interaction volume from real interaction timestamps." icon={CalendarClock}>
          {interactionTrendData.length ? (
            <MiniLineChart data={interactionTrendData} />
          ) : (
            <EmptyState
              icon={CalendarClock}
              title="No interaction trend data"
              description="Log more interactions to render an activity chart."
            />
          )}
        </InsightCard>

        <InsightCard title="Follow-up completion trends" subtitle="Historical completion series are not exposed yet." icon={CheckCircle2}>
          <EmptyState
            icon={CheckCircle2}
            title="Historical completion trends unavailable"
            description="The backend returns current follow-up status counts, but not completion timestamps needed for a true trend line. Current state distribution is shown elsewhere on this page."
          />
        </InsightCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <InsightCard title="Opportunity conversion metrics" subtitle="User effectiveness metrics from the backend metrics service." icon={Sparkles}>
          {metrics?.user_effectiveness ? (
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                <p className="text-xs uppercase tracking-wide text-white/35">Conversion rate</p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {Math.round(metrics.user_effectiveness.opportunities.opportunity_conversion_rate * 100)}%
                </p>
              </div>
              <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                <p className="text-xs uppercase tracking-wide text-white/35">Completed follow-ups</p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {metrics.user_effectiveness.opportunities.completed_follow_ups}
                </p>
              </div>
              <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                <p className="text-xs uppercase tracking-wide text-white/35">Tracked follow-ups</p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {metrics.user_effectiveness.opportunities.tracked_follow_ups}
                </p>
              </div>
            </div>
          ) : (
            <EmptyState title="No opportunity metrics yet" description="Backend effectiveness metrics are not available for this user yet." />
          )}
        </InsightCard>

        <InsightCard title="Recommendation effectiveness" subtitle="Acceptance and rejection from real feedback signals." icon={Lightbulb}>
          {metrics?.user_effectiveness ? (
            <DonutChart segments={recommendationEffectivenessSegments} />
          ) : (
            <EmptyState title="No recommendation effectiveness yet" description="Give feedback on recommendations to populate this section." />
          )}
        </InsightCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <InsightCard title="Follow-up state distribution" subtitle="Current completion state from analytics summary counts." icon={CheckCircle2}>
          <DonutChart segments={followUpStateSegments} />
        </InsightCard>

        <InsightCard title="Actionable relationship list" subtitle="Use filtered relationships to jump into action." icon={TrendingUp}>
          {topRelationships.length === 0 ? (
            <EmptyState title="No filtered relationships" description="Adjust the filters above to widen the dataset." />
          ) : (
            <div className="space-y-3">
              {topRelationships.map((item) => (
                <div key={item.contact_id} className="rounded-xl border border-white/6 bg-white/[0.03] px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-white">{item.name}</p>
                      <p className="mt-1 text-xs text-white/40 capitalize">
                        {item.relationship_strength} • {item.relationship_risk} risk
                      </p>
                    </div>
                    <ScoreBadge score={item.score} size="sm" />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      onClick={() => navigate(`/contacts/${item.contact_id}`)}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/70 hover:bg-white/10 hover:text-white transition-colors"
                    >
                      Open contact profile
                    </button>
                    <button
                      onClick={() => setFollowUpTarget(item)}
                      className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/70 hover:bg-white/10 hover:text-white transition-colors"
                    >
                      <Plus className="h-4 w-4" />
                      Create follow-up
                    </button>
                    <button
                      onClick={() => handleGenerate(item)}
                      className="inline-flex items-center gap-2 rounded-xl border border-accent/25 bg-accent/12 px-3 py-2 text-sm font-medium text-accent hover:bg-accent/20 transition-colors"
                    >
                      <Sparkles className="h-4 w-4" />
                      Generate prep
                    </button>
                    <button
                      onClick={() => navigate("/recommendations")}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/70 hover:bg-white/10 hover:text-white transition-colors"
                    >
                      Jump to recommendations
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </InsightCard>
      </div>

      <Modal open={Boolean(followUpTarget)} onClose={() => setFollowUpTarget(null)} title="Create follow-up">
        {followUpTarget && (
          <FollowUpForm
            contactId={followUpTarget.contact_id}
            initialValues={{
              title: `Follow up with ${followUpTarget.name}`,
              description: `Relationship score is ${Math.round(followUpTarget.score)} with ${followUpTarget.relationship_risk} risk.`,
            }}
            onSubmit={handleCreateFollowUp}
            onCancel={() => setFollowUpTarget(null)}
            submitting={submittingFollowUp}
          />
        )}
      </Modal>
    </motion.div>
  );
}
