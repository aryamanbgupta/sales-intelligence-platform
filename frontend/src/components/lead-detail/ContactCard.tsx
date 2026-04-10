import type { ContactOut } from "@/lib/types";

const CONFIDENCE_DOT: Record<string, string> = {
  high: "bg-emerald-500",
  medium: "bg-amber-500",
  low: "bg-slate-400",
};

export default function ContactCard({ contact }: { contact: ContactOut }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-slate-50/50 px-4 py-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium truncate">
            {contact.full_name || "Unknown"}
          </p>
          {contact.confidence && (
            <span
              className={`h-1.5 w-1.5 rounded-full shrink-0 ${CONFIDENCE_DOT[contact.confidence] || CONFIDENCE_DOT.low}`}
              title={`${contact.confidence} confidence`}
            />
          )}
        </div>
        {contact.title && (
          <p className="text-xs text-muted">{contact.title}</p>
        )}
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        {contact.email && (
          <a
            href={`mailto:${contact.email}`}
            className="inline-flex items-center justify-center h-7 w-7 rounded border border-border bg-white hover:bg-slate-50 transition-colors"
            title={`Email ${contact.email}`}
          >
            <svg className="h-3.5 w-3.5 text-muted" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
            </svg>
          </a>
        )}
        {contact.phone && (
          <a
            href={`tel:${contact.phone}`}
            className="inline-flex items-center justify-center h-7 w-7 rounded border border-border bg-white hover:bg-slate-50 transition-colors"
            title={`Call ${contact.phone}`}
          >
            <svg className="h-3.5 w-3.5 text-muted" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
            </svg>
          </a>
        )}
        {contact.linkedin_url && (
          <a
            href={contact.linkedin_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center h-7 w-7 rounded border border-border bg-white hover:bg-slate-50 transition-colors"
            title="LinkedIn"
          >
            <svg className="h-3.5 w-3.5 text-muted" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
            </svg>
          </a>
        )}
      </div>
    </div>
  );
}
