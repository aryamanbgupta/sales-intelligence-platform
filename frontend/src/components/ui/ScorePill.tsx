import { getScoreTier } from "@/lib/utils";

export default function ScorePill({ score }: { score: number | null }) {
  const tier = getScoreTier(score);
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={`h-2.5 w-2.5 rounded-full ${tier.pill}`}
      />
      <span className="font-semibold tabular-nums text-sm">
        {score ?? "N/A"}
      </span>
    </span>
  );
}
