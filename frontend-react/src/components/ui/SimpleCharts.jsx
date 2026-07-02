import { motion } from "framer-motion";

export function MiniBarChart({ data = [], valueFormatter = (value) => value, colorClass = "bg-accent" }) {
  const maxValue = Math.max(...data.map((item) => item.value || 0), 1);

  if (!data.length) {
    return <p className="text-sm text-white/35">No chart data available.</p>;
  }

  return (
    <div className="space-y-3">
      {data.map((item) => (
        <div key={item.label} className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-white/45">
            <span>{item.label}</span>
            <span>{valueFormatter(item.value)}</span>
          </div>
          <div className="h-2 rounded-full bg-white/6 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(item.value / maxValue) * 100}%` }}
              transition={{ duration: 0.35 }}
              className={`h-full rounded-full ${colorClass}`}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function MiniLineChart({ data = [] }) {
  if (!data.length) {
    return <p className="text-sm text-white/35">No chart data available.</p>;
  }

  const maxValue = Math.max(...data.map((item) => item.value || 0), 1);
  const stepX = data.length > 1 ? 100 / (data.length - 1) : 100;
  const points = data
    .map((item, index) => {
      const x = data.length === 1 ? 50 : index * stepX;
      const y = 100 - ((item.value || 0) / maxValue) * 100;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="space-y-3">
      <div className="h-44 rounded-2xl border border-white/6 bg-white/[0.03] p-4">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full overflow-visible">
          <polyline
            fill="none"
            stroke="rgba(124, 92, 255, 0.95)"
            strokeWidth="2.5"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={points}
          />
          {data.map((item, index) => {
            const x = data.length === 1 ? 50 : index * stepX;
            const y = 100 - ((item.value || 0) / maxValue) * 100;
            return <circle key={item.label} cx={x} cy={y} r="2.6" fill="rgba(34, 211, 238, 0.95)" />;
          })}
        </svg>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {data.map((item) => (
          <div key={item.label} className="rounded-xl border border-white/6 bg-white/[0.03] px-3 py-2">
            <p className="text-xs text-white/35">{item.label}</p>
            <p className="mt-1 text-sm font-medium text-white">{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function DonutChart({ segments = [], size = 132 }) {
  const total = segments.reduce((sum, segment) => sum + (segment.value || 0), 0);

  if (!segments.length || total === 0) {
    return <p className="text-sm text-white/35">No chart data available.</p>;
  }

  const strokeWidth = 14;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  let cumulative = 0;

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={strokeWidth}
          fill="none"
        />
        {segments.map((segment) => {
          const portion = (segment.value || 0) / total;
          const dash = portion * circumference;
          const offset = circumference - cumulative * circumference;
          cumulative += portion;
          return (
            <circle
              key={segment.label}
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke={segment.color}
              strokeWidth={strokeWidth}
              fill="none"
              strokeDasharray={`${dash} ${circumference - dash}`}
              strokeDashoffset={offset}
              strokeLinecap="round"
              transform={`rotate(-90 ${size / 2} ${size / 2})`}
            />
          );
        })}
      </svg>

      <div className="grid flex-1 gap-2">
        {segments.map((segment) => (
          <div
            key={segment.label}
            className="flex items-center justify-between rounded-xl border border-white/6 bg-white/[0.03] px-3 py-2"
          >
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: segment.color }} />
              <span className="text-sm text-white/65">{segment.label}</span>
            </div>
            <span className="text-sm font-medium text-white">{segment.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
