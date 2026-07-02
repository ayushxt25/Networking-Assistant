const BASE_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

function getToken() {
  return localStorage.getItem("access_token");
}

let unauthorizedHandler = null;

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

async function request(path, { method = "GET", body, auth = true, timeout = 30000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    clearTimeout(timer);

    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }

    if (res.status === 401 && auth) {
      if (unauthorizedHandler) unauthorizedHandler();
      const error = new Error(data?.detail || "Session expired. Please log in again.");
      error.status = 401;
      throw error;
    }

    if (!res.ok) {
      const message = data?.detail || `Request failed with status ${res.status}`;
      const error = new Error(message);
      error.status = res.status;
      throw error;
    }

    return data;
  } catch (err) {
    clearTimeout(timer);
    if (err.name === "AbortError") {
      throw new Error("Request timed out. Please check your connection and try again.");
    }
    throw err;
  }
}

// Helper to build a query string from a params object, skipping undefined/null/empty values.
function buildQuery(params = {}) {
  const cleaned = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== ""
  );
  if (cleaned.length === 0) return "";
  const search = new URLSearchParams(cleaned.map(([k, v]) => [k, String(v)]));
  return `?${search.toString()}`;
}

export const api = {
  register: (username, password) =>
    request("/auth/register", { method: "POST", body: { username, password }, auth: false }),

  login: (username, password) =>
    request("/auth/login", { method: "POST", body: { username, password }, auth: false }),

  generateConversation: (description, interests) =>
    request("/generate-conversation", {
      method: "POST",
      body: { description, interests },
      timeout: 60000,
    }),

  sendFeedback: (suggestion, action) =>
    request("/feedback", { method: "POST", body: { suggestion, action } }),

  submitFeedback: (body) =>
    request("/feedback", { method: "POST", body }),

  factCheck: (query) =>
    request("/fact-check", { method: "POST", body: { query } }),

  getHistory: () => request("/history", { method: "GET" }),

  getFeedbackHistory: () => request("/feedback-history", { method: "GET" }),

  analyzeEvent: (description, candidateLabels) =>
    request("/analyze-event", {
      method: "POST",
      body: { description, candidate_labels: candidateLabels },
    }),

  contacts: {
    list: (params) => request(`/contacts${buildQuery(params)}`, { method: "GET" }),
    get: (id) => request(`/contacts/${id}`, { method: "GET" }),
    create: (body) => request("/contacts", { method: "POST", body }),
    update: (id, body) => request(`/contacts/${id}`, { method: "PUT", body }),
    remove: (id) => request(`/contacts/${id}`, { method: "DELETE" }),
  },

  events: {
    list: (params) => request(`/events${buildQuery(params)}`, { method: "GET" }),
    get: (id) => request(`/events/${id}`, { method: "GET" }),
    create: (body) => request("/events", { method: "POST", body }),
    update: (id, body) => request(`/events/${id}`, { method: "PUT", body }),
    remove: (id) => request(`/events/${id}`, { method: "DELETE" }),
  },

  interactions: {
    list: (params) => request(`/interactions${buildQuery(params)}`, { method: "GET" }),
    get: (id) => request(`/interactions/${id}`, { method: "GET" }),
    create: (body) => request("/interactions", { method: "POST", body }),
    update: (id, body) => request(`/interactions/${id}`, { method: "PUT", body }),
    remove: (id) => request(`/interactions/${id}`, { method: "DELETE" }),
  },

  followUps: {
    list: (params) => request(`/follow-ups${buildQuery(params)}`, { method: "GET" }),
    get: (id) => request(`/follow-ups/${id}`, { method: "GET" }),
    create: (body) => request("/follow-ups", { method: "POST", body }),
    update: (id, body) => request(`/follow-ups/${id}`, { method: "PUT", body }),
    remove: (id) => request(`/follow-ups/${id}`, { method: "DELETE" }),
  },

  relationshipScores: {
    list: (contactId) =>
      request(`/relationships/scores${buildQuery({ contact_id: contactId })}`, { method: "GET" }),
  },

  recommendations: {
    list: (params) => request(`/recommendations${buildQuery(params)}`, { method: "GET" }),
    nextBestActions: (limit) =>
      request(`/recommendations/next-best-actions${buildQuery({ limit })}`, { method: "GET" }),
  },

  opportunities: {
    list: () => request("/opportunities", { method: "GET" }),
  },

  network: {
    graphInsights: () => request("/network/graph-insights", { method: "GET" }),
  },

  analytics: {
    summary: () => request("/analytics/summary", { method: "GET" }),
  },

  metrics: {
    get: () => request("/metrics", { method: "GET" }),
    summary: () => request("/metrics/summary", { method: "GET" }),
  },

  personalization: {
    profile: () => request("/personalization/profile", { method: "GET" }),
  },
};
