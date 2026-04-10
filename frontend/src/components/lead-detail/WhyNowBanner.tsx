export default function WhyNowBanner({ text }: { text: string | null | undefined }) {
  if (!text) return null;

  return (
    <div className="border-l-2 border-orange-500 pl-5 py-3">
      <h3
        className="text-xs font-medium text-orange-600 uppercase tracking-widest mb-1.5"
        style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
      >
        Why Now
      </h3>
      <p className="text-base font-light leading-relaxed">{text}</p>
    </div>
  );
}
