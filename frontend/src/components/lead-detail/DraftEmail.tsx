import CopyButton from "@/components/ui/CopyButton";

export default function DraftEmail({ email }: { email: string | null | undefined }) {
  if (!email) return null;

  // Try to extract subject line if present
  const subjectMatch = email.match(/^Subject:\s*(.+?)(?:\n|$)/i);
  const subject = subjectMatch ? subjectMatch[1].trim() : null;
  const body = subject ? email.replace(/^Subject:\s*.+?\n+/i, "").trim() : email;

  return (
    <div className="bg-card rounded-lg border border-border shadow-sm p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-muted uppercase tracking-wider">
          Draft Outreach Email
        </h3>
        <CopyButton text={email} />
      </div>

      {subject && (
        <p className="text-sm font-semibold mb-3">
          Subject: {subject}
        </p>
      )}

      <div className="text-sm leading-relaxed text-muted whitespace-pre-wrap bg-slate-50 rounded-md p-4 border border-border">
        {body}
      </div>
    </div>
  );
}
