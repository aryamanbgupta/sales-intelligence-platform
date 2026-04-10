export default function WhyNowBanner({ text }: { text: string | null | undefined }) {
  if (!text) return null;

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-5 py-4">
      <h3 className="text-xs font-semibold text-amber-800 uppercase tracking-wider mb-1.5">
        Why Now
      </h3>
      <p className="text-sm text-amber-900 leading-relaxed">{text}</p>
    </div>
  );
}
