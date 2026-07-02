import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export function useRelationshipScores() {
  const [scores, setScores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchScores = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.relationshipScores.list();
      setScores(data?.scores || []);
    } catch (err) {
      setError(err.message || "Failed to load relationship scores.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScores();
  }, [fetchScores]);

  return { scores, loading, error, refetch: fetchScores };
}