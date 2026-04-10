import Link from "next/link";
import type { LeadListItem } from "@/lib/types";
import ScorePill from "@/components/ui/ScorePill";
import CertBadge from "@/components/ui/CertBadge";
import StarRating from "@/components/ui/StarRating";
import { formatDistance } from "@/lib/utils";

export default function LeadRow({ lead }: { lead: LeadListItem }) {
  return (
    <Link
      href={`/leads/${lead.id}`}
      className="grid grid-cols-[60px_1fr_150px_140px_70px] items-center gap-4 px-5 py-3.5 border-b border-border hover:bg-slate-50/70 transition-colors"
    >
      <div>
        <ScorePill score={lead.lead_score} />
      </div>
      <div className="min-w-0">
        <p className="font-medium text-sm truncate">{lead.name}</p>
        <p className="text-xs text-muted truncate">
          {[lead.city, lead.state].filter(Boolean).join(", ")}
          {lead.years_in_business && (
            <span> &middot; {lead.years_in_business} yrs</span>
          )}
        </p>
      </div>
      <div>
        <CertBadge certification={lead.certification} />
      </div>
      <div>
        <StarRating rating={lead.rating} reviewCount={lead.review_count} />
      </div>
      <div className="text-xs text-muted tabular-nums text-right">
        {formatDistance(lead.distance_miles)}
      </div>
    </Link>
  );
}
