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
    <div>
      <h3
        className="text-xs font-medium text-muted uppercase tracking-widest mb-3"
        style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
      >
        {title}
      </h3>
      <ul className="space-y-2.5">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2.5 text-sm leading-relaxed font-light">
            <span className={`shrink-0 mt-2 h-1.5 w-1.5 rounded-full ${accentColor}`} />
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
    <div className="grid gap-8 sm:grid-cols-2 border-t border-neutral-200 pt-8">
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
