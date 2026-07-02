import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Plus, Mail, Link2, Building2, Trash2 } from "lucide-react";
import { useContactProfile } from "../hooks/useContactProfile";
import { api } from "../api/client";
import ScoreBadge from "../components/ui/ScoreBadge";
import ErrorState from "../components/ui/ErrorState";
import EmptyState from "../components/ui/EmptyState";
import { SkeletonLine, SkeletonCard } from "../components/ui/SkeletonLoader";
import Modal from "../components/ui/Modal";
import InteractionForm from "../components/domain/InteractionForm";
import FollowUpForm from "../components/domain/FollowUpForm";

export default function ContactProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { contact, score, interactions, followUps, loading, error, refetch } = useContactProfile(id);
  const [interactionModalOpen, setInteractionModalOpen] = useState(false);
  const [followUpModalOpen, setFollowUpModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleLogInteraction(payload) {
    setSubmitting(true);
    try {
      await api.interactions.create(payload);
      setInteractionModalOpen(false);
      refetch();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAddFollowUp(payload) {
    setSubmitting(true);
    try {
      await api.followUps.create(payload);
      setFollowUpModalOpen(false);
      refetch();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete ${contact.name}? This can't be undone.`)) return;
    await api.contacts.remove(id);
    navigate("/contacts");
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-4">
        <SkeletonLine width="30%" height="1.75rem" />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorState message={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
    >
      <button
        onClick={() => navigate("/contacts")}
        className="flex items-center gap-1.5 text-sm text-white/50 hover:text-white transition-colors mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to contacts
      </button>

      <div className="glass rounded-xl p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-white">{contact.name}</h1>
            {(contact.role || contact.company) && (
              <p className="text-white/50 mt-1 flex items-center gap-1.5">
                <Building2 className="w-4 h-4" />
                {[contact.role, contact.company].filter(Boolean).join(" at ")}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <ScoreBadge score={score} />
            <button
              onClick={handleDelete}
              className="p-2 rounded-lg text-white/40 hover:text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-4 mt-4 text-sm text-white/50">
          {contact.email && (
            <a href={`mailto:${contact.email}`} className="flex items-center gap-1.5 hover:text-white transition-colors">
              <Mail className="w-4 h-4" />
              {contact.email}
            </a>
          )}
          {contact.linkedin_url && (
            <a href={contact.linkedin_url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 hover:text-white transition-colors">
              <Link2 className="w-4 h-4" />
              LinkedIn
            </a>
          )}
        </div>

        {contact.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-4">
            {contact.tags.map((tag) => (
              <span key={tag} className="px-2 py-1 rounded-full text-xs bg-white/5 text-white/60">
                {tag}
              </span>
            ))}
          </div>
        )}

        {contact.notes && <p className="text-sm text-white/70 mt-4 leading-relaxed">{contact.notes}</p>}

        <div className="flex gap-2 mt-6">
          <button
            onClick={() => setInteractionModalOpen(true)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-accent/15 text-accent text-sm font-medium hover:bg-accent/25 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Log interaction
          </button>
          <button
            onClick={() => setFollowUpModalOpen(true)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 text-white text-sm font-medium hover:bg-white/10 transition-colors border border-white/10"
          >
            <Plus className="w-4 h-4" />
            Add follow-up
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-3">Follow-ups</h2>
          {followUps.length === 0 ? (
            <EmptyState title="No follow-ups" description="Nothing scheduled for this contact." />
          ) : (
            <div className="flex flex-col gap-2">
              {followUps.map((f) => (
                <div key={f.id} className="glass rounded-lg p-3">
                  <p className="text-sm text-white font-medium">{f.title}</p>
                  {f.due_date && (
                    <p className="text-xs text-white/40 mt-1">
                      Due {new Date(f.due_date).toLocaleDateString()}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <h2 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-3">Timeline</h2>
          {interactions.length === 0 ? (
            <EmptyState title="No interactions yet" description="Log your first interaction with this contact." />
          ) : (
            <div className="flex flex-col gap-2">
              {interactions.map((i) => (
                <div key={i.id} className="glass rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white font-medium capitalize">{i.interaction_type}</span>
                    <span className="text-xs text-white/40">
                      {new Date(i.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {i.notes && <p className="text-sm text-white/60 mt-1">{i.notes}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <Modal open={interactionModalOpen} onClose={() => setInteractionModalOpen(false)} title="Log interaction">
        <InteractionForm
          contactId={Number(id)}
          onSubmit={handleLogInteraction}
          onCancel={() => setInteractionModalOpen(false)}
          submitting={submitting}
        />
      </Modal>

      <Modal open={followUpModalOpen} onClose={() => setFollowUpModalOpen(false)} title="Add follow-up">
        <FollowUpForm
          contactId={Number(id)}
          onSubmit={handleAddFollowUp}
          onCancel={() => setFollowUpModalOpen(false)}
          submitting={submitting}
        />
      </Modal>
    </motion.div>
  );
}