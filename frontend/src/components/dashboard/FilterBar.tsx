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
  { value: "hot", label: `Hot (${SCORE_TIERS.HOT.min}+)` },
  { value: "warm", label: "Warm (40-59)" },
  { value: "cold", label: "Cold (<40)" },
];

const CERT_OPTIONS = [
  { value: "", label: "All Certifications" },
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
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
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
          className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900/10 placeholder:text-slate-400"
        />
      </div>

      {/* Filters row */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Score tier chips */}
        <div className="flex items-center gap-1.5">
          {TIER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onScoreTierChange(opt.value)}
              className={`px-3 py-1 text-xs font-medium rounded-full border transition-colors cursor-pointer ${
                scoreTier === opt.value
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white text-muted border-border hover:border-slate-400"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Certification dropdown */}
        <select
          value={certification}
          onChange={(e) => onCertificationChange(e.target.value)}
          className="text-xs border border-border rounded-lg px-3 py-1.5 bg-white text-muted focus:outline-none focus:ring-2 focus:ring-slate-900/10 cursor-pointer"
        >
          {CERT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
