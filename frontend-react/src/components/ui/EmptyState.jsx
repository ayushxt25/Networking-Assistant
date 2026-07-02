export default function EmptyState({ icon: Icon, title, description, actionLabel, onAction }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-4">
      {Icon && (
        <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-4">
          <Icon className="w-6 h-6 text-white/40" />
        </div>
      )}
      <h3 className="text-white font-medium mb-1">{title}</h3>
      {description && <p className="text-sm text-white/50 max-w-sm mb-4">{description}</p>}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="px-4 py-2 rounded-lg bg-accent/15 text-accent text-sm font-medium hover:bg-accent/25 transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
