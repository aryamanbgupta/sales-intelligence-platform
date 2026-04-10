"use client";

import { useState } from "react";

export default function ResearchSummary({
  summary,
  citations,
}: {
  summary: string | null | undefined;
  citations: string[];
}) {
  const [expanded, setExpanded] = useState(false);

  if (!summary && citations.length === 0) return null;

  return (
    <div className="space-y-3">
      {/* Collapsible research summary */}
      {summary && (
        <div className="bg-card rounded-lg border border-border shadow-sm overflow-hidden">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between px-5 py-3 text-xs font-semibold text-muted uppercase tracking-wider hover:bg-slate-50/50 transition-colors cursor-pointer"
          >
            Research Summary
            <svg
              className={`h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
          {expanded && (
            <div className="px-5 pb-4 text-sm leading-relaxed text-muted whitespace-pre-wrap border-t border-border pt-3">
              {summary}
            </div>
          )}
        </div>
      )}

      {/* Citations */}
      {citations.length > 0 && (
        <div className="px-1">
          <h4 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">
            Sources
          </h4>
          <div className="flex flex-wrap gap-2">
            {citations.map((url, i) => {
              let label: string;
              try {
                label = new URL(url).hostname.replace("www.", "");
              } catch {
                label = url;
              }
              return (
                <a
                  key={i}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:text-blue-800 underline underline-offset-2"
                >
                  {label}
                </a>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
