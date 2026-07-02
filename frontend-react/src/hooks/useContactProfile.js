import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export function useContactProfile(contactId) {
  const [contact, setContact] = useState(null);
  const [score, setScore] = useState(null);
  const [interactions, setInteractions] = useState([]);
  const [followUps, setFollowUps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [contactData, scoreData, interactionsData, followUpsData] = await Promise.all([
        api.contacts.get(contactId),
        api.relationshipScores.list(contactId).catch(() => null),
        api.interactions.list({ contact_id: contactId, sort_order: "desc" }),
        api.followUps.list({ contact_id: contactId, sort_by: "due_date", sort_order: "asc" }),
      ]);

      setContact(contactData);
      setScore(scoreData?.scores?.[0]?.score ?? null);
      setInteractions(interactionsData);
      setFollowUps(followUpsData);
    } catch (err) {
      setError(err.message || "Failed to load contact.");
    } finally {
      setLoading(false);
    }
  }, [contactId]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { contact, score, interactions, followUps, loading, error, refetch: fetchAll };
}