function InsightList({
  title,
  items,
  accentColor,
}: {
  title: string;
  items: string[];
  accentColor: string;
}) {
  if (items.length === 0) return null;

  return (
    <div className="bg-card rounded-lg border border-border shadow-sm p-5">
      <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
        {title}
      </h3>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-sm leading-relaxed">
            <span className={`shrink-0 mt-1.5 h-1.5 w-1.5 rounded-full ${accentColor}`} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function InsightsGrid({
  buyingSignals,
  painPoints,
}: {
  buyingSignals: string[];
  painPoints: string[];
}) {
  if (buyingSignals.length === 0 && painPoints.length === 0) return null;

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <InsightList
        title="Buying Signals"
        items={buyingSignals}
        accentColor="bg-emerald-500"
      />
      <InsightList
        title="Pain Points"
        items={painPoints}
        accentColor="bg-red-400"
      />
    </div>
  );
}
