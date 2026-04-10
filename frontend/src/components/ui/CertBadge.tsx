import { CERT_CONFIG, CERT_DEFAULT } from "@/lib/constants";

export default function CertBadge({
  certification,
}: {
  certification: string | null;
}) {
  const config = (certification && CERT_CONFIG[certification]) || CERT_DEFAULT;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${config.color}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
      {certification || "Uncertified"}
    </span>
  );
}
