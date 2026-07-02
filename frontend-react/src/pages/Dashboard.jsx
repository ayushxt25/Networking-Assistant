import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ListChecks, TrendingUp, Sparkles, ArrowRight, AlertCircle } from "lucide-react";
import { useFollowUps, groupFollowUps } from "../hooks/useFollowUps";
import { useRecommendations } from "../hooks/useRecommendations";
import { useRelationshipScores } from "../hooks/useRelationshipScores";
import { useAuth } from "../context/AuthContext";
import ScoreBadge from "../components/ui/ScoreBadge";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import { SkeletonCard } from "../components/ui/SkeletonLoader";

function WidgetCard({ title, icon: Icon, viewAllHref, children }) {
  const navigate = useNavigate();
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="glass rounded-xl p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-accent" />
          <h2 className="text-sm font-medium text-white">{title}</h2>
        </div>
        {viewAllHref && (
          <button
            onClick={() => navigate(viewAllHref)}
            className="flex items-center gap-1 text-xs text-white/40 hover:text-white transition-colors"
          >
            View all
            <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>
      {children}
    </motion.div>
  );
}

function FollowUpsWidget() {
  const { followUps, loading, error, refetch } = useFollowUps();
  const navigate = useNavigate();

  if (loading) return <SkeletonCard />;
  if (error) return <ErrorState message={error} onRetry={refetch} />;

  const groups = groupFollowUps(followUps);
  const dueSoon = [...groups.overdue, ...groups.today].slice(0, 4);

  return (
    <WidgetCard title="Due soon" icon={ListChecks} viewAllHref="/follow-ups">
      {dueSoon.length === 0 ? (
        <EmptyState title="Nothing due" description="You're on top of things." />
      ) : (
        <div className="flex flex-col gap-2">
          {dueSoon.map((f) => (
            <button
              key={f.id}
              onClick={() => f.contact_id && navigate(`/contacts/${f.contact_id}`)}
              className="text-left flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] transition-colors"
            >
              <span className="text-sm text-white/80 truncate">{f.title}</span>
              {f.due_date && (
                <span className="text-xs text-white/40 shrink-0 ml-2">
                  {new Date(f.due_date).toLocaleDateString()}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </WidgetCard>
  );
}

function RecommendationsWidget() {
  const { recommendations, loading, error, refetch } = useRecommendations(4);
  const navigate = useNavigate();

  if (loading) return <SkeletonCard />;
  if (error) return <ErrorState message={error} onRetry={refetch} />;

  return (
    <WidgetCard title="Who to reach out to" icon={Sparkles}>
      {recommendations.length === 0 ? (
        <EmptyState title="No recommendations yet" description="Add contacts and interactions to get suggestions." />
      ) : (
        <div className="flex flex-col gap-2">
          {recommendations.map((r, i) => {
            const label = r.title || r.summary || r.reasoning || r.recommendation_type || "Recommended action";
            const contactId = r.contact_id ?? r.target_id;
            return (
              <button
                key={r.id ?? i}
                onClick={() => contactId && navigate(`/contacts/${contactId}`)}
                className="text-left flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] transition-colors"
              >
                <span className="text-sm text-white/80 truncate">{label}</span>
                {r.priority_score !== undefined && r.priority_score !== null && (
                  <span className="text-xs text-accent shrink-0 ml-2 font-medium">
                    {Math.round(r.priority_score * 100) / 100}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </WidgetCard>
  );
}

function RelationshipHealthWidget() {
  const { scores, loading, error, refetch } = useRelationshipScores();
  const navigate = useNavigate();

  if (loading) return <SkeletonCard />;
  if (error) return <ErrorState message={error} onRetry={refetch} />;

  const atRisk = scores.filter((s) => s.relationship_risk === "high" || s.score < 50).slice(0, 4);

  return (
    <WidgetCard title="Relationship health" icon={TrendingUp} viewAllHref="/contacts">
      {atRisk.length === 0 ? (
        <EmptyState
          icon={scores.length === 0 ? AlertCircle : undefined}
          title={scores.length === 0 ? "No scores yet" : "Everything looks steady"}
          description={
            scores.length === 0
              ? "Log interactions with contacts to build relationship scores."
              : "No relationships need immediate attention."
          }
        />
      ) : (
        <div className="flex flex-col gap-2">
          {atRisk.map((s) => (
            <button
              key={s.contact_id}
              onClick={() => navigate(`/contacts/${s.contact_id}`)}
              className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] transition-colors"
            >
              <span className="text-sm text-white/80 truncate">{s.name}</span>
              <ScoreBadge score={s.score} size="sm" showLabel={false} />
            </button>
          ))}
        </div>
      )}
    </WidgetCard>
  );
}

export default function Dashboard() {
  const { username } = useAuth();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
    >
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-white">
          {greeting}{username ? `, ${username}` : ""}
        </h1>
        <p className="text-sm text-white/50 mt-1">Here's what needs your attention today.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <FollowUpsWidget />
        <RecommendationsWidget />
        <RelationshipHealthWidget />
      </div>
    </motion.div>
  );
}