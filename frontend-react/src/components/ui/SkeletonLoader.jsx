export function SkeletonLine({ width = "100%", height = "1rem" }) {
  return (
    <div
      className="rounded-md bg-white/5 animate-pulse"
      style={{ width, height }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="glass rounded-xl p-4 flex flex-col gap-3">
      <SkeletonLine width="40%" height="0.75rem" />
      <SkeletonLine width="60%" height="1.5rem" />
    </div>
  );
}

export function SkeletonRow({ columns = 4 }) {
  return (
    <div className="flex items-center gap-4 px-4 py-3 border-b border-white/5">
      {Array.from({ length: columns }).map((_, i) => (
        <SkeletonLine key={i} width={i === 0 ? "20%" : "15%"} />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, columns = 4 }) {
  return (
    <div className="glass rounded-xl overflow-hidden">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} columns={columns} />
      ))}
    </div>
  );
}