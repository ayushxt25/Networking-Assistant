import { motion } from "framer-motion";

export default function StatCard({ label, value, icon: Icon, trend, onClick }) {
  const Wrapper = onClick ? motion.button : motion.div;

  return (
    <Wrapper
      onClick={onClick}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`glass rounded-xl p-4 flex flex-col gap-2 text-left w-full ${
        onClick ? "hover:border-white/15 transition-colors cursor-pointer" : ""
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm text-white/50">{label}</span>
        {Icon && <Icon className="w-4 h-4 text-white/40" />}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-semibold text-white">{value}</span>
        {trend !== undefined && trend !== null && (
          <span className={`text-xs font-medium ${trend >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {trend >= 0 ? "+" : ""}
            {trend}
          </span>
        )}
      </div>
    </Wrapper>
  );
}