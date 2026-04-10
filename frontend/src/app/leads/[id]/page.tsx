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
      <div className="mx-auto max-w-4xl px-6 py-8">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-muted hover:text-foreground transition-colors mb-6"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
          Back to leads
        </Link>
        <div className="bg-card rounded-lg border border-border shadow-sm p-8 text-center">
          <p className="text-muted">Lead not found or backend is unavailable.</p>
        </div>
      </div>
    );
  }

  const insights = lead.insights;

  return (
    <div className="mx-auto max-w-4xl px-6 py-8 space-y-5">
      {/* Back link */}
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-foreground transition-colors"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
        Back to leads
      </Link>

      {/* Header card with contacts */}
      <LeadHeader lead={lead} />

      {/* Why Now urgency banner */}
      <WhyNowBanner text={insights?.why_now} />

      {/* Talking Points + Score Breakdown side by side */}
      {insights && (
        <div className="grid gap-4 sm:grid-cols-2">
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

      {/* Recommended Pitch */}
      {insights?.recommended_pitch && (
        <div className="bg-card rounded-lg border border-border shadow-sm p-5">
          <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">
            Recommended Pitch
          </h3>
          <p className="text-sm leading-relaxed">{insights.recommended_pitch}</p>
        </div>
      )}

      {/* Draft Email */}
      <DraftEmail email={insights?.draft_email} />

      {/* Research Summary + Citations */}
      <ResearchSummary
        summary={insights?.research_summary}
        citations={insights?.citations || []}
      />

      {/* No insights fallback */}
      {!insights && (
        <div className="bg-card rounded-lg border border-border shadow-sm p-8 text-center">
          <p className="text-muted text-sm">
            This lead has not been enriched yet. Run the enrichment pipeline to generate insights.
          </p>
        </div>
      )}
    </div>
  );
}
