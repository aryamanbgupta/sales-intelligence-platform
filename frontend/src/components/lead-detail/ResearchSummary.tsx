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
    <div className="space-y-4 border-t border-neutral-200 pt-8">
      {/* Collapsible research summary */}
      {summary && (
        <div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between py-2 cursor-pointer group"
          >
            <span
              className="text-xs font-medium text-muted uppercase tracking-widest group-hover:text-foreground transition-colors"
              style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
            >
              Research Summary
            </span>
            <svg
              className={`h-4 w-4 text-muted transition-transform ${expanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
          {expanded && (
            <div className="text-sm leading-relaxed text-muted font-light whitespace-pre-wrap pt-3 pb-2">
              {summary}
            </div>
          )}
        </div>
      )}

      {/* Citations */}
      {citations.length > 0 && (
        <div>
          <h4
            className="text-xs font-medium text-muted uppercase tracking-widest mb-3"
            style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
          >
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
                  className="px-2.5 py-0.5 text-xs rounded-full border border-neutral-300 text-muted hover:border-neutral-900 hover:text-foreground transition-colors"
                  style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
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
