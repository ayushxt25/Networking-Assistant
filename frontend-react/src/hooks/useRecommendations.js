import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export function useRecommendations(limit = 5) {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRecommendations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.recommendations.nextBestActions(limit);
      setRecommendations(data);
    } catch (err) {
      setError(err.message || "Failed to load recommendations.");
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchRecommendations();
  }, [fetchRecommendations]);

  return { recommendations, loading, error, refetch: fetchRecommendations };
}