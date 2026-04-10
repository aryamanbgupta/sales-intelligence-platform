import { SCORE_BREAKDOWN_LABELS } from "@/lib/constants";
import ProgressBar from "@/components/ui/ProgressBar";

export default function ScoreBreakdown({
  breakdown,
}: {
  breakdown: Record<string, number>;
}) {
  if (!breakdown || Object.keys(breakdown).length === 0) return null;

  return (
    <div className="bg-card rounded-lg border border-border shadow-sm p-5">
      <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
        Score Breakdown
      </h3>
      <div className="space-y-2.5">
        {Object.entries(SCORE_BREAKDOWN_LABELS).map(([key, { label, max }]) => (
          <ProgressBar
            key={key}
            label={label}
            value={breakdown[key] ?? 0}
            max={max}
          />
        ))}
      </div>
    </div>
  );
}
