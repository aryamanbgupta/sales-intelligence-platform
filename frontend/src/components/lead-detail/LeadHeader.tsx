import type { LeadDetail } from "@/lib/types";
import ScorePill from "@/components/ui/ScorePill";
import CertBadge from "@/components/ui/CertBadge";
import StarRating from "@/components/ui/StarRating";
import ContactCard from "./ContactCard";
import { formatPhone, cleanUrl, formatDistance } from "@/lib/utils";

export default function LeadHeader({ lead }: { lead: LeadDetail }) {
  const location = [lead.address, lead.city, lead.state, lead.zip_code]
    .filter(Boolean)
    .join(", ");

  return (
    <div className="bg-card rounded-lg border border-border shadow-sm p-6 space-y-5">
      {/* Top row: name + score */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1.5">
          <h1 className="text-2xl font-bold">{lead.name}</h1>
          <CertBadge certification={lead.certification} />
        </div>
        <div className="text-right shrink-0">
          <div className="text-3xl font-bold">
            <ScorePill score={lead.insights?.lead_score ?? null} />
          </div>
        </div>
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
        {location && <span>{location}</span>}
        {lead.phone && (
          <>
            <span className="text-border">&middot;</span>
            <a href={`tel:${lead.phone}`} className="hover:text-foreground transition-colors">
              {formatPhone(lead.phone)}
            </a>
          </>
        )}
        {lead.website && (
          <>
            <span className="text-border">&middot;</span>
            <a
              href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              {cleanUrl(lead.website)}
            </a>
          </>
        )}
        {lead.years_in_business && (
          <>
            <span className="text-border">&middot;</span>
            <span>{lead.years_in_business} yrs in business</span>
          </>
        )}
        {lead.distance_miles !== null && (
          <>
            <span className="text-border">&middot;</span>
            <span>{formatDistance(lead.distance_miles)}</span>
          </>
        )}
      </div>

      {/* Rating */}
      <StarRating rating={lead.rating} reviewCount={lead.review_count} />

      {/* Contacts */}
      {lead.contacts.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-muted uppercase tracking-wider">
            Key Contacts
          </h3>
          <div className="grid gap-2 sm:grid-cols-2">
            {lead.contacts.map((c) => (
              <ContactCard key={c.id} contact={c} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
