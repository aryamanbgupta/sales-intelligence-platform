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
    <div className="bg-card rounded-lg border border-border px-5 py-4 shadow-sm">
      <p className={`text-2xl font-bold tabular-nums ${accent || "text-foreground"}`}>
        {value}
      </p>
      <p className="text-xs text-muted mt-0.5">{label}</p>
    </div>
  );
}

export default function StatsBar({ stats }: { stats: StatsResponse | null }) {
  if (!stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-card rounded-lg border border-border px-5 py-4 shadow-sm animate-pulse">
            <div className="h-7 w-16 bg-slate-100 rounded mb-1" />
            <div className="h-3 w-20 bg-slate-100 rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard value={stats.total_leads} label="Total Leads" />
      <StatCard
        value={(stats.score_distribution["51-75"] ?? 0) + (stats.score_distribution["76-100"] ?? 0)}
        label="Top Leads (51+)"
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
