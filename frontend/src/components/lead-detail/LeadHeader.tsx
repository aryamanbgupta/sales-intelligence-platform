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
    <div className="space-y-6">
      {/* Name + Score row */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-3">
          <h1 className="text-4xl font-light leading-tight">{lead.name}</h1>
          <div className="flex items-center gap-2">
            <CertBadge certification={lead.certification} />
            <StarRating rating={lead.rating} reviewCount={lead.review_count} />
          </div>
        </div>
        <div className="shrink-0">
          <ScorePill score={lead.insights?.lead_score ?? null} size="lg" />
        </div>
      </div>

      {/* Meta — thin top border, editorial style */}
      <div className="border-t border-neutral-900 pt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
        {location && <span>{location}</span>}
        {lead.phone && (
          <>
            <span className="text-neutral-300">&middot;</span>
            <a href={`tel:${lead.phone}`} className="hover:text-foreground transition-colors">
              {formatPhone(lead.phone)}
            </a>
          </>
        )}
        {lead.website && (
          <>
            <span className="text-neutral-300">&middot;</span>
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
            <span className="text-neutral-300">&middot;</span>
            <span>{lead.years_in_business} yrs in business</span>
          </>
        )}
        {lead.distance_miles !== null && (
          <>
            <span className="text-neutral-300">&middot;</span>
            <span>{formatDistance(lead.distance_miles)}</span>
          </>
        )}
      </div>

      {/* Contacts */}
      {lead.contacts.length > 0 && (
        <div className="space-y-3">
          <h3
            className="text-xs font-medium text-muted uppercase tracking-widest"
            style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
          >
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
