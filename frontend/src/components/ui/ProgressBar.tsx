export default function ProgressBar({
  label,
  value,
  max,
}: {
  label: string;
  value: number;
  max: number;
}) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const barColor =
    pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-slate-400";

  return (
    <div className="flex items-center gap-3">
      <span className="w-32 text-xs text-muted shrink-0 text-right">
        {label}
      </span>
      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-muted w-12 shrink-0">
        {value}/{max}
      </span>
    </div>
  );
}
