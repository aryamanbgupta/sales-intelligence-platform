import { getScoreTier } from "@/lib/utils";

export default function ScorePill({ score, size = "sm" }: { score: number | null; size?: "sm" | "lg" }) {
  const tier = getScoreTier(score);
  const isLg = size === "lg";

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full font-mono font-semibold tabular-nums ${tier.pill} text-white ${
        isLg ? "px-4 py-1.5 text-base" : "px-2.5 py-0.5 text-xs"
      }`}
      style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
    >
      {score ?? "N/A"}
    </span>
  );
}
