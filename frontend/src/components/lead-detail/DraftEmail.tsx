import CopyButton from "@/components/ui/CopyButton";

export default function DraftEmail({ email }: { email: string | null | undefined }) {
  if (!email) return null;

  // Try to extract subject line
  const subjectMatch = email.match(/^Subject:\s*(.+?)(?:\n|$)/i);
  const subject = subjectMatch ? subjectMatch[1].trim() : null;
  const body = subject ? email.replace(/^Subject:\s*.+?\n+/i, "").trim() : email;

  return (
    <div className="bg-dark rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3
          className="text-xs font-medium text-neutral-400 uppercase tracking-widest"
          style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
        >
          Draft Outreach Email
        </h3>
        <CopyButton text={email} />
      </div>

      {subject && (
        <p className="text-sm font-medium text-white">
          Subject: {subject}
        </p>
      )}

      <div
        className="text-sm leading-relaxed text-neutral-300 font-light whitespace-pre-wrap rounded-xl p-4"
        style={{ background: "rgba(38,38,38,0.5)", border: "1px solid #262626" }}
      >
        {body}
      </div>
    </div>
  );
}
