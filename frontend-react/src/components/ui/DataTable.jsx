import { motion } from "framer-motion";
import { SkeletonTable } from "./SkeletonLoader";
import EmptyState from "./EmptyState";
import ErrorState from "./ErrorState";

export default function DataTable({
  columns,
  data,
  loading,
  error,
  onRetry,
  onRowClick,
  emptyIcon,
  emptyTitle = "Nothing here yet",
  emptyDescription,
  emptyActionLabel,
  onEmptyAction,
}) {
  if (loading) return <SkeletonTable columns={columns.length} />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (!data || data.length === 0) {
    return (
      <div className="glass rounded-xl">
        <EmptyState
          icon={emptyIcon}
          title={emptyTitle}
          description={emptyDescription}
          actionLabel={emptyActionLabel}
          onAction={onEmptyAction}
        />
      </div>
    );
  }

  return (
    <div className="glass rounded-xl overflow-hidden">
      <div className="grid" style={{ gridTemplateColumns: columns.map((c) => c.width || "1fr").join(" ") }}>
        {columns.map((col) => (
          <div
            key={col.key}
            className="px-4 py-3 text-xs font-medium text-white/40 uppercase tracking-wide border-b border-white/5"
          >
            {col.label}
          </div>
        ))}
      </div>

      {data.map((row, i) => (
        <motion.div
          key={row.id ?? i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2, delay: Math.min(i * 0.03, 0.3) }}
          onClick={() => onRowClick?.(row)}
          className={`grid border-b border-white/5 last:border-b-0 ${
            onRowClick ? "hover:bg-white/[0.03] cursor-pointer transition-colors" : ""
          }`}
          style={{ gridTemplateColumns: columns.map((c) => c.width || "1fr").join(" ") }}
        >
          {columns.map((col) => (
            <div key={col.key} className="px-4 py-3 text-sm text-white/80 flex items-center">
              {col.render ? col.render(row) : row[col.key]}
            </div>
          ))}
        </motion.div>
      ))}
    </div>
  );
}