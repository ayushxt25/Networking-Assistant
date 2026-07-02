import { useState } from "react";

export default function InteractionForm({ contactId, onSubmit, onCancel, submitting }) {
  const [interactionType, setInteractionType] = useState("call");
  const [notes, setNotes] = useState("");
  const [sentiment, setSentiment] = useState("neutral");
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    try {
      await onSubmit({
        contact_id: contactId,
        interaction_type: interactionType,
        notes: notes.trim() || null,
        sentiment,
      });
    } catch (err) {
      setError(err.message || "Couldn't log this interaction.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      {error && <p className="text-sm text-red-400">{error}</p>}

      <select
        value={interactionType}
        onChange={(e) => setInteractionType(e.target.value)}
        className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent/50"
      >
        <option value="call">Call</option>
        <option value="email">Email</option>
        <option value="meeting">Meeting</option>
        <option value="message">Message</option>
        <option value="event">Event</option>
      </select>

      <select
        value={sentiment}
        onChange={(e) => setSentiment(e.target.value)}
        className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent/50"
      >
        <option value="positive">Positive</option>
        <option value="neutral">Neutral</option>
        <option value="negative">Negative</option>
      </select>

      <textarea
        placeholder="What happened?"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={3}
        className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50 resize-none"
      />

      <div className="flex justify-end gap-2 mt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded-lg text-sm text-white/60 hover:text-white transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
        >
          {submitting ? "Logging..." : "Log interaction"}
        </button>
      </div>
    </form>
  );
}