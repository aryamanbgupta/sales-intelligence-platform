import Link from "next/link";
import { getLead } from "@/lib/api";
import LeadHeader from "@/components/lead-detail/LeadHeader";
import WhyNowBanner from "@/components/lead-detail/WhyNowBanner";
import TalkingPoints from "@/components/lead-detail/TalkingPoints";
import ScoreBreakdown from "@/components/lead-detail/ScoreBreakdown";
import InsightsGrid from "@/components/lead-detail/InsightsGrid";
import DraftEmail from "@/components/lead-detail/DraftEmail";
import ResearchSummary from "@/components/lead-detail/ResearchSummary";

export default async function LeadDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let lead;
  try {
    lead = await getLead(Number(id));
  } catch {
    return (
      <div className="mx-auto max-w-4xl px-6 py-12">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted uppercase tracking-widest hover:text-foreground transition-colors mb-8"
          style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
          Back to leads
        </Link>
        <div className="border border-neutral-200 p-12 text-center">
          <p className="text-muted font-light">Lead not found or backend is unavailable.</p>
        </div>
      </div>
    );
  }

  const insights = lead.insights;

  return (
    <div className="mx-auto max-w-4xl px-6 py-12 space-y-8">
      {/* Back link — monospace eyebrow style */}
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-muted uppercase tracking-widest hover:text-foreground transition-colors"
        style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
        Back to leads
      </Link>

      {/* Header — name, score, cert, contacts */}
      <LeadHeader lead={lead} />

      {/* Why Now — left-border accent */}
      <WhyNowBanner text={insights?.why_now} />

      {/* Talking Points + Score Breakdown — side by side */}
      {insights && (
        <div className="grid gap-8 sm:grid-cols-2 border-t border-neutral-200 pt-8">
          <TalkingPoints points={insights.talking_points} />
          <ScoreBreakdown breakdown={insights.score_breakdown} />
        </div>
      )}

      {/* Buying Signals + Pain Points */}
      {insights && (
        <InsightsGrid
          buyingSignals={insights.buying_signals}
          painPoints={insights.pain_points}
        />
      )}

      {/* Recommended Pitch — left-border accent like Instalily testimonial style */}
      {insights?.recommended_pitch && (
        <div className="border-l-2 border-neutral-900 pl-5 py-2">
          <h3
            className="text-xs font-medium text-muted uppercase tracking-widest mb-2"
            style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
          >
            Recommended Pitch
          </h3>
          <p className="text-base font-light leading-relaxed">{insights.recommended_pitch}</p>
        </div>
      )}

      {/* Draft Email — dark card (Instalily dark section feel) */}
      <DraftEmail email={insights?.draft_email} />

      {/* Research Summary + Citations */}
      <ResearchSummary
        summary={insights?.research_summary}
        citations={insights?.citations || []}
      />

      {/* No insights fallback */}
      {!insights && (
        <div className="border border-neutral-200 p-12 text-center">
          <p className="text-muted text-sm font-light">
            This lead has not been enriched yet. Run the enrichment pipeline to generate insights.
          </p>
        </div>
      )}
    </div>
  );
}
