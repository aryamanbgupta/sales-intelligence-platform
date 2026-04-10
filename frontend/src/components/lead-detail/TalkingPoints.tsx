export default function TalkingPoints({ points }: { points: string[] }) {
  if (points.length === 0) return null;

  return (
    <div>
      <h3
        className="text-xs font-medium text-muted uppercase tracking-widest mb-4"
        style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
      >
        Talking Points
      </h3>
      <ol className="space-y-3">
        {points.map((point, i) => (
          <li key={i} className="flex gap-3 text-sm leading-relaxed">
            <span
              className="shrink-0 text-xs font-semibold text-neutral-400 mt-0.5 w-5"
              style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
            >
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="font-light">{point}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
