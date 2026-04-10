export const SCORE_TIERS = {
  HOT: { min: 60, label: "Hot", color: "#f97316", bg: "bg-orange-100", text: "text-orange-700", ring: "ring-orange-500", pill: "bg-orange-500" },
  WARM: { min: 40, label: "Warm", color: "#eab308", bg: "bg-yellow-100", text: "text-yellow-700", ring: "ring-yellow-500", pill: "bg-yellow-500" },
  COLD: { min: 0, label: "Cold", color: "#94a3b8", bg: "bg-slate-100", text: "text-slate-600", ring: "ring-slate-400", pill: "bg-slate-400" },
} as const;

export const CERT_CONFIG: Record<string, { color: string; dot: string; label: string }> = {
  "President's Club": { color: "text-amber-700", dot: "bg-amber-500", label: "President's Club" },
  "Master Elite": { color: "text-blue-700", dot: "bg-blue-500", label: "Master Elite" },
};

export const CERT_DEFAULT = { color: "text-slate-500", dot: "bg-slate-300", label: "Uncertified" };

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
