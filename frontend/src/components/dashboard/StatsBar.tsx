import type { StatsResponse } from "@/lib/types";

function StatCard({
  value,
  label,
  accent,
}: {
  value: string | number;
  label: string;
  accent?: string;
}) {
  return (
    <div className="border-r border-b border-neutral-900 px-5 py-5 last:border-r-0">
      <p
        className={`text-3xl font-light tabular-nums ${accent || "text-foreground"}`}
      >
        {value}
      </p>
      <p
        className="text-xs text-muted mt-1 uppercase tracking-widest font-medium"
        style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
      >
        {label}
      </p>
    </div>
  );
}

export default function StatsBar({ stats }: { stats: StatsResponse | null }) {
  if (!stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 border-t border-l border-neutral-900">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="border-r border-b border-neutral-900 px-5 py-5 animate-pulse">
            <div className="h-8 w-16 bg-neutral-100 rounded mb-2" />
            <div className="h-3 w-24 bg-neutral-100 rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 border-t border-l border-neutral-900">
      <StatCard value={stats.total_leads} label="Total Leads" />
      <StatCard
        value={(stats.score_distribution["51-75"] ?? 0) + (stats.score_distribution["76-100"] ?? 0)}
        label="Top Leads"
        accent="text-orange-600"
      />
      <StatCard
        value={stats.avg_score !== null ? stats.avg_score.toFixed(1) : "N/A"}
        label="Avg Score"
      />
      <StatCard
        value={`${Object.values(stats.score_distribution).reduce((a, b) => a + b, 0)}/${stats.total_leads}`}
        label="Enriched"
      />
    </div>
  );
}
