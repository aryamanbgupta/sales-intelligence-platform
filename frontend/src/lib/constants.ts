export const SCORE_TIERS = {
  HOT: { min: 60, label: "Hot", color: "#f97316", bg: "bg-orange-50", text: "text-orange-700", pill: "bg-orange-500" },
  WARM: { min: 40, label: "Warm", color: "#eab308", bg: "bg-amber-50", text: "text-amber-700", pill: "bg-amber-500" },
  COLD: { min: 0, label: "Cold", color: "#737373", bg: "bg-neutral-100", text: "text-neutral-600", pill: "bg-neutral-400" },
} as const;

export const CERT_CONFIG: Record<string, { color: string; dot: string; pillBg: string; pillText: string; label: string }> = {
  "President's Club": { color: "text-amber-700", dot: "bg-amber-500", pillBg: "bg-neutral-900", pillText: "text-white", label: "President's Club" },
  "Master Elite": { color: "text-blue-700", dot: "bg-blue-500", pillBg: "bg-neutral-900", pillText: "text-white", label: "Master Elite" },
};

export const CERT_DEFAULT = { color: "text-neutral-500", dot: "bg-neutral-300", pillBg: "bg-neutral-200", pillText: "text-neutral-600", label: "Uncertified" };

export const SORT_OPTIONS = [
  { value: "lead_score", label: "Score" },
  { value: "name", label: "Name" },
  { value: "rating", label: "Rating" },
  { value: "review_count", label: "Reviews" },
  { value: "distance_miles", label: "Distance" },
] as const;

export const SCORE_BREAKDOWN_LABELS: Record<string, { label: string; max: number }> = {
  certification_tier: { label: "Certification", max: 30 },
  review_volume: { label: "Review Volume", max: 20 },
  rating_quality: { label: "Rating Quality", max: 10 },
  business_signals: { label: "Business Signals", max: 20 },
  why_now_urgency: { label: "Why Now", max: 20 },
};

export const PER_PAGE_OPTIONS = [20, 50] as const;
