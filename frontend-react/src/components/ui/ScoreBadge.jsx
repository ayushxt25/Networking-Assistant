const TIERS = [
  { min: 80, label: "Strong", classes: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20" },
  { min: 50, label: "Steady", classes: "bg-accent/15 text-accent border-accent/20" },
  { min: 0, label: "At risk", classes: "bg-red-500/15 text-red-400 border-red-500/20" },
];

function getTier(score) {
  return TIERS.find((t) => score >= t.min) ?? TIERS[TIERS.length - 1];
}

export default function ScoreBadge({ score, showLabel = true, size = "md" }) {
  if (score === null || score === undefined) {
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border border-white/10 text-white/40">
        No score
      </span>
    );
  }

  const tier = getTier(score);
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium border ${sizeClasses} ${tier.classes}`}
    >
      <span className="font-semibold">{Math.round(score)}</span>
      {showLabel && <span className="opacity-80">{tier.label}</span>}
    </span>
  );
}