import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

function isSameDay(a, b) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function groupFollowUps(followUps) {
  const now = new Date();
  const groups = { overdue: [], today: [], upcoming: [], noDate: [] };

  for (const f of followUps) {
    if (f.status === "completed") continue;
    if (!f.due_date) {
      groups.noDate.push(f);
      continue;
    }
    const due = new Date(f.due_date);
    if (isSameDay(due, now)) {
      groups.today.push(f);
    } else if (due < now) {
      groups.overdue.push(f);
    } else {
      groups.upcoming.push(f);
    }
  }

  return groups;
}

export function useFollowUps({ statusFilter } = {}) {
  const [followUps, setFollowUps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchFollowUps = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.followUps.list({
        status: statusFilter,
        sort_by: "due_date",
        sort_order: "asc",
        limit: 100,
      });
      setFollowUps(data);
    } catch (err) {
      setError(err.message || "Failed to load follow-ups.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchFollowUps();
  }, [fetchFollowUps]);

  return { followUps, loading, error, refetch: fetchFollowUps };
}