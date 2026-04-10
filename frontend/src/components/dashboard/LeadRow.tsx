import Link from "next/link";
import type { LeadListItem } from "@/lib/types";
import ScorePill from "@/components/ui/ScorePill";
import CertBadge from "@/components/ui/CertBadge";
import { formatDistance, getVolumeTier } from "@/lib/utils";

export default function LeadRow({ lead }: { lead: LeadListItem }) {
  const volume = getVolumeTier(lead.review_count);

  return (
    <Link
      href={`/leads/${lead.id}`}
      className="grid grid-cols-[56px_1fr_120px_72px] items-center gap-4 px-5 py-4 border-b border-neutral-200 hover:bg-neutral-50 transition-colors"
    >
      <div>
        <ScorePill score={lead.lead_score} />
      </div>
      <div className="min-w-0">
        <p className="font-medium text-sm truncate">{lead.name}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-muted">
            {[lead.city, lead.state].filter(Boolean).join(", ")}
            {lead.years_in_business && (
              <span className="text-neutral-400"> &middot; {lead.years_in_business} yrs</span>
            )}
          </span>
          <CertBadge certification={lead.certification} />
        </div>
      </div>
      <div>
        <span
          className={`text-xs font-medium ${volume.style}`}
          style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
        >
          {volume.label}
        </span>
        {lead.review_count !== null && lead.review_count > 0 && (
          <p className="text-[10px] text-neutral-400 mt-0.5" style={{ fontFamily: "var(--font-ibm-plex-mono)" }}>
            {lead.review_count} reviews
          </p>
        )}
      </div>
      <div
        className="text-xs text-muted tabular-nums text-right"
        style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
      >
        {formatDistance(lead.distance_miles)}
      </div>
    </Link>
  );
}
