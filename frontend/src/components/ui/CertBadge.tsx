import { CERT_CONFIG, CERT_DEFAULT } from "@/lib/constants";

export default function CertBadge({
  certification,
}: {
  certification: string | null;
}) {
  const config = (certification && CERT_CONFIG[certification]) || CERT_DEFAULT;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${config.pillBg} ${config.pillText}`}
      style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
    >
      {certification || "Uncertified"}
    </span>
  );
}
