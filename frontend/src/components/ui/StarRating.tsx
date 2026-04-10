export default function StarRating({
  rating,
  reviewCount,
}: {
  rating: number | null;
  reviewCount?: number | null;
}) {
  if (rating === null) return <span className="text-xs text-slate-400">No rating</span>;

  const fullStars = Math.floor(rating);
  const hasHalf = rating - fullStars >= 0.3;

  return (
    <span className="inline-flex items-center gap-1">
      <span className="text-amber-500 text-sm" aria-label={`${rating} stars`}>
        {"★".repeat(fullStars)}
        {hasHalf && "½"}
        {"☆".repeat(5 - fullStars - (hasHalf ? 1 : 0))}
      </span>
      <span className="text-xs text-muted tabular-nums">
        {rating.toFixed(1)}
        {reviewCount !== undefined && reviewCount !== null && (
          <span className="text-slate-400"> ({reviewCount})</span>
        )}
      </span>
    </span>
  );
}
