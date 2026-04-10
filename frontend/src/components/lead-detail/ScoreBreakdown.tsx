import { SCORE_BREAKDOWN_LABELS } from "@/lib/constants";
import ProgressBar from "@/components/ui/ProgressBar";

export default function ScoreBreakdown({
  breakdown,
}: {
  breakdown: Record<string, number>;
}) {
  if (!breakdown || Object.keys(breakdown).length === 0) return null;

  return (
    <div>
      <h3
        className="text-xs font-medium text-muted uppercase tracking-widest mb-4"
        style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
      >
        Score Breakdown
      </h3>
      <div className="space-y-3">
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
