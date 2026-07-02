import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Users2, Search } from "lucide-react";
import { motion } from "framer-motion";
import { useContacts } from "../hooks/useContacts";
import { api } from "../api/client";
import DataTable from "../components/ui/DataTable";
import ScoreBadge from "../components/ui/ScoreBadge";
import Modal from "../components/ui/Modal";
import ContactForm from "../components/domain/ContactForm";

export default function Contacts() {
  const [q, setQ] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const { contacts, loading, error, refetch } = useContacts({ q });

  async function handleCreate(payload) {
    setSubmitting(true);
    try {
      await api.contacts.create(payload);
      setModalOpen(false);
      refetch();
    } finally {
      setSubmitting(false);
    }
  }

  const columns = [
    { key: "name", label: "Name", width: "2fr" },
    { key: "company", label: "Company", width: "1.5fr", render: (r) => r.company || "—" },
    { key: "role", label: "Role", width: "1.5fr", render: (r) => r.role || "—" },
    {
      key: "score",
      label: "Score",
      width: "1fr",
      render: (r) => <ScoreBadge score={r.score} size="sm" />,
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
          <h1 className="text-xl font-semibold text-white">Contacts</h1>
          <p className="text-sm text-white/50 mt-1">Everyone you're building a relationship with.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add contact
        </button>
      </div>

      <div className="relative mb-4">
        <Search className="w-4 h-4 text-white/30 absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Search contacts..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
        />
      </div>

      <DataTable
        columns={columns}
        data={contacts}
        loading={loading}
        error={error}
        onRetry={refetch}
        onRowClick={(row) => navigate(`/contacts/${row.id}`)}
        emptyIcon={Users2}
        emptyTitle="No contacts yet"
        emptyDescription="Add your first contact to start tracking the relationship."
        emptyActionLabel="Add contact"
        onEmptyAction={() => setModalOpen(true)}
      />

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add contact">
        <ContactForm onSubmit={handleCreate} onCancel={() => setModalOpen(false)} submitting={submitting} />
      </Modal>
    </motion.div>
  );
}