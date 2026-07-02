import { useState } from "react";
import { Plus, CalendarDays, Search, MapPin } from "lucide-react";
import { motion } from "framer-motion";
import { useEvents } from "../hooks/useEvents";
import { api } from "../api/client";
import DataTable from "../components/ui/DataTable";
import Modal from "../components/ui/Modal";
import EventForm from "../components/domain/EventForm";

export default function Events() {
  const [q, setQ] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { events, loading, error, refetch } = useEvents({ q });

  async function handleCreate(payload) {
    setSubmitting(true);
    try {
      await api.events.create(payload);
      setModalOpen(false);
      refetch();
    } finally {
      setSubmitting(false);
    }
  }

  const columns = [
    { key: "title", label: "Event", width: "2fr" },
    {
      key: "location",
      label: "Location",
      width: "1.5fr",
      render: (r) =>
        r.location ? (
          <span className="flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-white/30" />
            {r.location}
          </span>
        ) : (
          "—"
        ),
    },
    {
      key: "event_date",
      label: "Date",
      width: "1fr",
      render: (r) => (r.event_date ? new Date(r.event_date).toLocaleDateString() : "—"),
    },
    {
      key: "goals",
      label: "Goals",
      width: "1.5fr",
      render: (r) =>
        r.goals?.length ? (
          <div className="flex flex-wrap gap-1">
            {r.goals.slice(0, 2).map((g) => (
              <span key={g} className="px-2 py-0.5 rounded-full text-xs bg-white/5 text-white/50">
                {g}
              </span>
            ))}
            {r.goals.length > 2 && (
              <span className="text-xs text-white/30">+{r.goals.length - 2}</span>
            )}
          </div>
        ) : (
          "—"
        ),
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
    >
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-white">Events</h1>
          <p className="text-sm text-white/50 mt-1">Meetings, conferences, and everything you're prepping for.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add event
        </button>
      </div>

      <div className="relative mb-4">
        <Search className="w-4 h-4 text-white/30 absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Search events..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
        />
      </div>

      <DataTable
        columns={columns}
        data={events}
        loading={loading}
        error={error}
        onRetry={refetch}
        emptyIcon={CalendarDays}
        emptyTitle="No events yet"
        emptyDescription="Add an upcoming event to start prepping with AI-suggested themes."
        emptyActionLabel="Add event"
        onEmptyAction={() => setModalOpen(true)}
      />

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add event">
        <EventForm onSubmit={handleCreate} onCancel={() => setModalOpen(false)} submitting={submitting} />
      </Modal>
    </motion.div>
  );
}