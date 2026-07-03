import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const STORAGE_PREFIX = "networking-assistant:onboarding";

function onboardingKey(username) {
  return `${STORAGE_PREFIX}:${username || "anonymous"}`;
}

function safeJsonParse(value) {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function readPreference(username) {
  if (!username || typeof window === "undefined") {
    return { status: null };
  }

  return safeJsonParse(window.localStorage.getItem(onboardingKey(username))) || { status: null };
}

export function writeOnboardingPreference(username, status) {
  if (!username || typeof window === "undefined") return;
  window.localStorage.setItem(
    onboardingKey(username),
    JSON.stringify({
      status,
      updated_at: new Date().toISOString(),
    })
  );
}

export function clearOnboardingPreference(username) {
  if (!username || typeof window === "undefined") return;
  window.localStorage.removeItem(onboardingKey(username));
}

export function hasMeaningfulProfile(profile) {
  if (!profile) return false;

  return Boolean(
    profile.full_name?.trim() ||
      profile.headline?.trim() ||
      profile.preferred_tone?.trim() ||
      (Array.isArray(profile.goals) && profile.goals.length > 0) ||
      (Array.isArray(profile.interests) && profile.interests.length > 0)
  );
}

export function summarizeOnboarding(profile, contacts = [], events = [], followUps = []) {
  const profileComplete = hasMeaningfulProfile(profile);
  const hasContacts = contacts.length > 0;
  const hasEvents = events.length > 0;
  const hasFollowUps = followUps.length > 0;
  const hasActivity = hasEvents || hasFollowUps;

  return {
    profileComplete,
    hasContacts,
    hasEvents,
    hasFollowUps,
    hasActivity,
    needsOnboarding: !profileComplete || !hasContacts || !hasActivity,
  };
}

export function useOnboardingStatus(username) {
  const [profile, setProfile] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [events, setEvents] = useState([]);
  const [followUps, setFollowUps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshIndex, setRefreshIndex] = useState(0);
  const [preference, setPreference] = useState(() => readPreference(username));

  const refresh = useCallback(() => setRefreshIndex((value) => value + 1), []);

  const setPreferenceStatus = useCallback(
    (status) => {
      writeOnboardingPreference(username, status);
      setPreference(readPreference(username));
    },
    [username]
  );

  useEffect(() => {
    setPreference(readPreference(username));
  }, [username]);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const [profileResult, contactsResult, eventsResult, followUpsResult] = await Promise.allSettled([
          api.profile.getOptional(),
          api.contacts.list({ limit: 1 }),
          api.events.list({ limit: 1 }),
          api.followUps.list({ limit: 1 }),
        ]);

        if (!active) return;

        if (profileResult.status === "fulfilled") {
          setProfile(profileResult.value);
        } else {
          throw profileResult.reason;
        }

        if (contactsResult.status !== "fulfilled") throw contactsResult.reason;
        if (eventsResult.status !== "fulfilled") throw eventsResult.reason;
        if (followUpsResult.status !== "fulfilled") throw followUpsResult.reason;

        setContacts(contactsResult.value || []);
        setEvents(eventsResult.value || []);
        setFollowUps(followUpsResult.value || []);
      } catch (err) {
        if (active) {
          setError(err.message || "Failed to load onboarding state.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      active = false;
    };
  }, [refreshIndex, username]);

  const summary = useMemo(
    () => summarizeOnboarding(profile, contacts, events, followUps),
    [profile, contacts, events, followUps]
  );

  useEffect(() => {
    if (summary.needsOnboarding || !username) return;
    if (preference.status === "completed") return;
    setPreferenceStatus("completed");
  }, [preference.status, setPreferenceStatus, summary.needsOnboarding, username]);

  return {
    profile,
    contacts,
    events,
    followUps,
    loading,
    error,
    refresh,
    preference,
    setPreferenceStatus,
    ...summary,
  };
}
