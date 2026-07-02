import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const STORAGE_PREFIX = "networking-assistant:notifications:read";
const CLOSED_FOLLOW_UP_STATUSES = new Set(["done", "completed", "complete", "closed"]);

function getStorageKey(username) {
  return `${STORAGE_PREFIX}:${username || "anonymous"}`;
}

function readReadMap(username) {
  if (!username || typeof window === "undefined") return {};

  try {
    const value = window.localStorage.getItem(getStorageKey(username));
    return value ? JSON.parse(value) : {};
  } catch {
    return {};
  }
}

function writeReadMap(username, map) {
  if (!username || typeof window === "undefined") return;
  window.localStorage.setItem(getStorageKey(username), JSON.stringify(map));
}

function toTime(value) {
  if (!value) return null;
  const time = new Date(value).getTime();
  return Number.isFinite(time) ? time : null;
}

function formatRelativeBucket(dateValue) {
  const time = toTime(dateValue);
  if (!time) return "No date";

  const diffDays = Math.ceil((time - Date.now()) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return `${Math.abs(diffDays)}d overdue`;
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  return `In ${diffDays}d`;
}

function buildNotificationId(prefix, parts) {
  return [prefix, ...parts.filter(Boolean)].join(":");
}

function buildItem({ id, type, title, subtitle, priority, href, dateValue }) {
  return {
    id,
    type,
    title,
    subtitle,
    priority,
    href,
    dateValue,
    lifecycleStatus: "new",
    sortTime: toTime(dateValue) ?? 0,
  };
}

function deriveNotifications({ followUps, events, recommendations, opportunities, relationshipScores }) {
  const items = [];

  for (const followUp of followUps) {
    const status = (followUp.status || "").toLowerCase();
    const dueTime = toTime(followUp.due_date);
    if (CLOSED_FOLLOW_UP_STATUSES.has(status) || !dueTime) continue;

    const diffDays = Math.ceil((dueTime - Date.now()) / (1000 * 60 * 60 * 24));
    if (diffDays > 3) continue;

    items.push(
      buildItem({
        id: buildNotificationId("follow-up", [followUp.id, diffDays < 0 ? "overdue" : "soon"]),
        type: diffDays < 0 ? "overdue_follow_up" : "follow_up_due_soon",
        title: diffDays < 0 ? `Overdue follow-up: ${followUp.title}` : `Follow-up due soon: ${followUp.title}`,
        subtitle: `${formatRelativeBucket(followUp.due_date)}${followUp.description ? ` • ${followUp.description}` : ""}`,
        priority: diffDays < 0 ? 98 : 84 - Math.max(diffDays, 0) * 4,
        href: followUp.contact_id ? `/contacts/${followUp.contact_id}` : "/follow-ups",
        dateValue: followUp.due_date,
      })
    );
  }

  for (const event of events) {
    const eventTime = toTime(event.event_date);
    if (!eventTime) continue;

    const diffDays = Math.ceil((eventTime - Date.now()) / (1000 * 60 * 60 * 24));
    if (diffDays < 0 || diffDays > 7) continue;

    items.push(
      buildItem({
        id: buildNotificationId("event", [event.id, "upcoming"]),
        type: "upcoming_event",
        title: `Upcoming event: ${event.title}`,
        subtitle: `${formatRelativeBucket(event.event_date)}${event.location ? ` • ${event.location}` : ""}`,
        priority: 76 - Math.max(diffDays, 0) * 3,
        href: "/events",
        dateValue: event.event_date,
      })
    );
  }

  for (const recommendation of recommendations) {
    if (Number(recommendation.priority_score || 0) < 75) continue;
    const lifecycleStatus = recommendation.lifecycle_status || "new";
    if (["dismissed", "completed"].includes(lifecycleStatus)) continue;

    items.push(
      buildItem({
        id: buildNotificationId("recommendation", [recommendation.recommendation_id]),
        type: "high_priority_recommendation",
        title: recommendation.title,
        subtitle: recommendation.reason || recommendation.description,
        priority: Number(recommendation.priority_score || 0),
        href: recommendation.related_contact_id ? `/contacts/${recommendation.related_contact_id}` : "/recommendations",
        dateValue: recommendation.created_at,
        lifecycleStatus,
      })
    );
  }

  for (const opportunity of opportunities) {
    if (Number(opportunity.priority_score || 0) < 75) continue;
    const lifecycleStatus = opportunity.lifecycle_status || "new";
    if (["dismissed", "completed"].includes(lifecycleStatus)) continue;

    items.push(
      buildItem({
        id: buildNotificationId("opportunity", [opportunity.opportunity_id]),
        type: "high_priority_opportunity",
        title: opportunity.title,
        subtitle: opportunity.reason || opportunity.description,
        priority: Number(opportunity.priority_score || 0),
        href: opportunity.related_contact_id ? `/contacts/${opportunity.related_contact_id}` : "/opportunities",
        dateValue: opportunity.created_at,
        lifecycleStatus,
      })
    );
  }

  for (const score of relationshipScores) {
    const numericScore = Number(score.score || 0);
    if ((score.relationship_risk || "").toLowerCase() !== "high" && numericScore > 45) continue;

    items.push(
      buildItem({
        id: buildNotificationId("relationship", [score.contact_id, score.relationship_risk, Math.round(numericScore)]),
        type: "relationship_needs_attention",
        title: `${score.name || "Relationship"} needs attention`,
        subtitle: `${score.relationship_risk || "medium"} risk • score ${Math.round(numericScore)}`,
        priority: 72 + Math.max(0, 40 - numericScore) * 0.4,
        href: score.contact_id ? `/contacts/${score.contact_id}` : "/relationship-scores",
        dateValue: score.updated_at || null,
      })
    );
  }

  return items
    .sort((a, b) => {
      if (b.priority !== a.priority) return b.priority - a.priority;
      return b.sortTime - a.sortTime;
    })
    .slice(0, 12);
}

export function useNotifications(username) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [readMap, setReadMap] = useState(() => readReadMap(username));
  const [data, setData] = useState({
    followUps: [],
    events: [],
    recommendations: [],
    opportunities: [],
    relationshipScores: [],
  });

  useEffect(() => {
    setReadMap(readReadMap(username));
  }, [username]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [followUps, events, recommendations, opportunities, relationshipScoresResponse] = await Promise.all([
        api.followUps.list({ limit: 20, sort_by: "due_date", sort_order: "asc" }),
        api.events.list({ limit: 20, sort_by: "event_date", sort_order: "asc" }),
        api.recommendations.nextBestActions(6),
        api.opportunities.list(),
        api.relationshipScores.list().catch(() => ({ scores: [] })),
      ]);

      setData({
        followUps: followUps || [],
        events: events || [],
        recommendations: recommendations || [],
        opportunities: opportunities || [],
        relationshipScores: relationshipScoresResponse?.scores || [],
      });
    } catch (err) {
      setError(err.message || "Failed to load notifications.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const notifications = useMemo(() => deriveNotifications(data), [data]);

  const unreadCount = useMemo(
    () => notifications.filter((item) => !readMap[item.id]).length,
    [notifications, readMap]
  );

  const markAsRead = useCallback(
    (id) => {
      const next = { ...readMap, [id]: new Date().toISOString() };
      setReadMap(next);
      writeReadMap(username, next);
    },
    [readMap, username]
  );

  const markAllAsRead = useCallback(() => {
    const next = { ...readMap };
    const timestamp = new Date().toISOString();

    for (const item of notifications) {
      next[item.id] = timestamp;
    }

    setReadMap(next);
    writeReadMap(username, next);
  }, [notifications, readMap, username]);

  return {
    loading,
    error,
    refresh,
    notifications,
    unreadCount,
    readMap,
    markAsRead,
    markAllAsRead,
    hasNotifications: notifications.length > 0,
  };
}
