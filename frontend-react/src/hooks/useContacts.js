import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export function useContacts({ q, sortBy = "created_at", sortOrder = "desc" } = {}) {
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchContacts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [contactsData, scoresData] = await Promise.all([
        api.contacts.list({ q, sort_by: sortBy, sort_order: sortOrder }),
        api.relationshipScores.list().catch(() => null),
      ]);

      const scoreMap = new Map();
      if (scoresData?.scores) {
        for (const s of scoresData.scores) {
          scoreMap.set(s.contact_id, s.score);
        }
      }

      const merged = contactsData.map((c) => ({
        ...c,
        score: scoreMap.get(c.id) ?? null,
      }));

      setContacts(merged);
    } catch (err) {
      setError(err.message || "Failed to load contacts.");
    } finally {
      setLoading(false);
    }
  }, [q, sortBy, sortOrder]);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  return { contacts, loading, error, refetch: fetchContacts };
}