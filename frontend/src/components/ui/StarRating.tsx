export default function StarRating({
  rating,
  reviewCount,
}: {
  rating: number | null;
  reviewCount?: number | null;
}) {
  if (rating === null) return <span className="text-xs text-neutral-400">No rating</span>;

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="text-amber-500 text-sm" aria-label={`${rating} stars`}>
        {"★".repeat(Math.floor(rating))}
        {rating - Math.floor(rating) >= 0.3 && "½"}
      </span>
      <span
        className="text-xs text-muted tabular-nums"
        style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
      >
        {rating.toFixed(1)}
        {reviewCount !== undefined && reviewCount !== null && (
          <span className="text-neutral-400"> ({reviewCount})</span>
        )}
      </span>
    </span>
  );
}
