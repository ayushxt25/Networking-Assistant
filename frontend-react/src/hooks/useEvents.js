import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export function useEvents({ q, sortBy = "created_at", sortOrder = "desc" } = {}) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.events.list({ q, sort_by: sortBy, sort_order: sortOrder });
      setEvents(data);
    } catch (err) {
      setError(err.message || "Failed to load events.");
    } finally {
      setLoading(false);
    }
  }, [q, sortBy, sortOrder]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  return { events, loading, error, refetch: fetchEvents };
}