import { SCORE_TIERS } from "./constants";

export function getScoreTier(score: number | null) {
  if (score === null) return SCORE_TIERS.COLD;
  if (score >= SCORE_TIERS.HOT.min) return SCORE_TIERS.HOT;
  if (score >= SCORE_TIERS.WARM.min) return SCORE_TIERS.WARM;
  return SCORE_TIERS.COLD;
}

export function formatPhone(phone: string | null): string {
  if (!phone) return "";
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  if (digits.length === 11 && digits[0] === "1") {
    return `(${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }
  return phone;
}

export function formatDistance(miles: number | null): string {
  if (miles === null) return "";
  return `${miles.toFixed(1)} mi`;
}

export function cleanUrl(url: string | null): string {
  if (!url) return "";
  return url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "");
}
