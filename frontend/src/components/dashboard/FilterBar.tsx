"use client";

import { SCORE_TIERS } from "@/lib/constants";

interface FilterBarProps {
  scoreTier: string;
  certification: string;
  search: string;
  onScoreTierChange: (tier: string) => void;
  onCertificationChange: (cert: string) => void;
  onSearchChange: (search: string) => void;
}

const TIER_OPTIONS = [
  { value: "", label: "All" },
  { value: "hot", label: `Hot ${SCORE_TIERS.HOT.min}+` },
  { value: "warm", label: "Warm" },
  { value: "cold", label: "Cold" },
];

const CERT_OPTIONS = [
  { value: "", label: "All Certs" },
  { value: "President's Club", label: "President's Club" },
  { value: "Master Elite", label: "Master Elite" },
];

export default function FilterBar({
  scoreTier,
  certification,
  search,
  onScoreTierChange,
  onCertificationChange,
  onSearchChange,
}: FilterBarProps) {
  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2}
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
          />
        </svg>
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search contractors..."
          className="w-full pl-9 pr-4 py-2.5 text-sm bg-white border border-neutral-200 rounded-none focus:outline-none focus:border-neutral-900 placeholder:text-neutral-400 transition-colors"
        />
      </div>

      {/* Filters row */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Score tier pills — Instalily dark pill style */}
        <div className="flex items-center gap-1.5">
          {TIER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onScoreTierChange(opt.value)}
              className={`px-3.5 py-1 text-xs font-semibold rounded-full border transition-colors cursor-pointer tracking-wide ${
                scoreTier === opt.value
                  ? "bg-neutral-900 text-white border-neutral-900"
                  : "bg-transparent text-muted border-neutral-300 hover:border-neutral-900"
              }`}
              style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="w-px h-5 bg-neutral-300" />

        {/* Certification pills */}
        <div className="flex items-center gap-1.5">
          {CERT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onCertificationChange(opt.value)}
              className={`px-3.5 py-1 text-xs font-semibold rounded-full border transition-colors cursor-pointer tracking-wide ${
                certification === opt.value
                  ? "bg-neutral-900 text-white border-neutral-900"
                  : "bg-transparent text-muted border-neutral-300 hover:border-neutral-900"
              }`}
              style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
