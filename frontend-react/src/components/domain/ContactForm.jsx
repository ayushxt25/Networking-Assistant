import { useState } from "react";

const emptyForm = {
  name: "",
  company: "",
  role: "",
  email: "",
  linkedin_url: "",
  notes: "",
  tags: "",
  relationship_strength: "",
};

export default function ContactForm({ initialValues, onSubmit, onCancel, submitting }) {
  const [form, setForm] = useState(() => ({
    ...emptyForm,
    ...initialValues,
    tags: initialValues?.tags?.join(", ") || "",
  }));
  const [error, setError] = useState(null);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (!form.name.trim()) {
      setError("Name is required.");
      return;
    }

    const payload = {
      name: form.name.trim(),
      company: form.company.trim() || null,
      role: form.role.trim() || null,
      email: form.email.trim() || null,
      linkedin_url: form.linkedin_url.trim() || null,
      notes: form.notes.trim() || null,
      tags: form.tags
        ? form.tags.split(",").map((t) => t.trim()).filter(Boolean)
        : null,
      relationship_strength: form.relationship_strength
        ? Number(form.relationship_strength)
        : null,
    };

    try {
      await onSubmit(payload);
    } catch (err) {
      setError(err.message || "Something went wrong saving this contact.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      {error && <p className="text-sm text-red-400">{error}</p>}

      <input
        type="text"
        placeholder="Name"
        value={form.name}
        onChange={(e) => update("name", e.target.value)}
        className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
      />
      <div className="grid grid-cols-2 gap-3">
        <input
          type="text"
          placeholder="Company"
          value={form.company}
          onChange={(e) => update("company", e.target.value)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
        />
        <input
          type="text"
          placeholder="Role"
          value={form.role}
          onChange={(e) => update("role", e.target.value)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
        />
      </div>
      <input
        type="email"
        placeholder="Email"
        value={form.email}
        onChange={(e) => update("email", e.target.value)}
        className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
      />
      <input
        type="text"
        placeholder="LinkedIn URL"
        value={form.linkedin_url}
        onChange={(e) => update("linkedin_url", e.target.value)}
        className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
      />
      <input
        type="text"
        placeholder="Tags (comma separated)"
        value={form.tags}
        onChange={(e) => update("tags", e.target.value)}
        className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
      />
      <textarea
        placeholder="Notes"
        value={form.notes}
        onChange={(e) => update("notes", e.target.value)}
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
          {submitting ? "Saving..." : "Save contact"}
        </button>
      </div>
    </form>
  );
}