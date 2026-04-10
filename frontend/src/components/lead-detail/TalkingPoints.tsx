export default function TalkingPoints({ points }: { points: string[] }) {
  if (points.length === 0) return null;

  return (
    <div className="bg-card rounded-lg border border-border shadow-sm p-5">
      <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
        Talking Points
      </h3>
      <ol className="space-y-2.5">
        {points.map((point, i) => (
          <li key={i} className="flex gap-3 text-sm leading-relaxed">
            <span className="shrink-0 h-5 w-5 rounded-full bg-slate-100 text-xs font-semibold text-muted flex items-center justify-center">
              {i + 1}
            </span>
            <span>{point}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
