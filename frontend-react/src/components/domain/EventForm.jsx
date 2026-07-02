import { useState, useEffect, useRef } from "react";
import { Sparkles } from "lucide-react";
import { api } from "../../api/client";

export default function EventForm({ onSubmit, onCancel, submitting }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [suggestedThemes, setSuggestedThemes] = useState([]);
  const [selectedThemes, setSelectedThemes] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (description.trim().length < 10) {
      setSuggestedThemes([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setAnalyzing(true);
      try {
        const result = await api.analyzeEvent(description.trim());
        setSuggestedThemes(result.themes || []);
      } catch {
        // Silent — theme suggestion is a nice-to-have, not required to submit the form.
        setSuggestedThemes([]);
      } finally {
        setAnalyzing(false);
      }
    }, 600);

    return () => clearTimeout(debounceRef.current);
  }, [description]);

  function toggleTheme(theme) {
    setSelectedThemes((prev) =>
      prev.includes(theme) ? prev.filter((t) => t !== theme) : [...prev, theme]
    );
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError("Title is required.");
      return;
    }

    const payload = {
      title: title.trim(),
      description: description.trim() || null,
      location: location.trim() || null,
      event_date: eventDate ? new Date(eventDate).toISOString() : null,
      goals: selectedThemes.length > 0 ? selectedThemes : null,
    };

    try {
      await onSubmit(payload);
    } catch (err) {
      setError(err.message || "Something went wrong saving this event.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      {error && <p className="text-sm text-red-400">{error}</p>}

      <input
        type="text"
        placeholder="Event title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
      />

      <div className="grid grid-cols-2 gap-3">
        <input
          type="text"
          placeholder="Location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
        />
        <input
          type="date"
          value={eventDate}
          onChange={(e) => setEventDate(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent/50"
        />
      </div>

      <textarea
        placeholder="Describe the event — themes will be suggested as you type"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={3}
        className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50 resize-none"
      />

      {(analyzing || suggestedThemes.length > 0) && (
        <div className="flex flex-col gap-2">
          <span className="text-xs text-white/40 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            {analyzing ? "Suggesting themes..." : "Suggested goals — tap to add"}
          </span>
          <div className="flex flex-wrap gap-1.5">
            {suggestedThemes.map((theme) => (
              <button
                key={theme}
                type="button"
                onClick={() => toggleTheme(theme)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                  selectedThemes.includes(theme)
                    ? "bg-accent/20 border-accent/40 text-accent"
                    : "bg-white/5 border-white/10 text-white/50 hover:text-white/80"
                }`}
              >
                {theme}
              </button>
            ))}
          </div>
        </div>
      )}

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
          {submitting ? "Saving..." : "Save event"}
        </button>
      </div>
    </form>
  );
}