"use client";

import { useEffect, useState } from "react";
import { getPipelineStatus } from "@/lib/api";
import type { PipelineStatusResponse } from "@/lib/types";

const STAGES = [
  {
    number: "01",
    title: "Scrape",
    engine: "Playwright + Coveo API",
    description:
      "Headless browser navigates GAF's contractor directory, intercepts the Coveo search API to extract structured JSON. Profile pages are scraped for website, years in business, and company description.",
    inputs: ["ZIP code", "Search radius"],
    outputs: [
      "Contractor name & address",
      "Certification tier",
      "Star rating & review count",
      "Phone, website, services",
      "GPS coordinates & distance",
    ],
    statusKey: "total_contractors" as const,
    statusLabel: "Contractors scraped",
  },
  {
    number: "02",
    title: "Research",
    engine: "Perplexity sonar-pro",
    description:
      'For each contractor, Perplexity searches the live web to build a research dossier. It finds decision-maker names, Google review themes, recent storm activity, growth signals, BBB data, and competitive positioning \u2014 all grounded with source citations.',
    inputs: ["Contractor name", "Address", "Certification"],
    outputs: [
      "Research summary (2\u20133 paragraphs)",
      "Source citations (URLs)",
      "Decision-maker names & titles",
      "Storm & weather signals",
      "Growth & hiring indicators",
    ],
    statusKey: "with_research" as const,
    statusLabel: "Researched",
  },
  {
    number: "03",
    title: "Score & Analyze",
    engine: "Python + OpenAI gpt-4o-mini",
    description:
      "Hybrid scoring: deterministic Python code scores objective factors (certification, reviews, rating) for 60/100 points. OpenAI reads the research text to score subjective signals (business growth, urgency) for 40/100 points. Also generates talking points, buying signals, pain points, pitch, and a draft outreach email.",
    inputs: ["Contractor data", "Research summary"],
    outputs: [
      "Lead score (0\u2013100)",
      "5-factor score breakdown",
      "Talking points (3\u20135)",
      "Buying signals & pain points",
      "Recommended pitch",
      "Why Now urgency signal",
      "Draft outreach email",
    ],
    statusKey: "with_scores" as const,
    statusLabel: "Scored",
  },
  {
    number: "04",
    title: "Extract Contacts",
    engine: "OpenAI gpt-4o-mini",
    description:
      "Parses decision-maker contact information from the research text. Extracts names, titles, emails, phone numbers, and LinkedIn URLs. Assigns confidence levels based on source authority. Multiple contacts per contractor are supported.",
    inputs: ["Research summary"],
    outputs: [
      "Full name & title",
      "Direct email",
      "Direct phone",
      "LinkedIn URL",
      "Confidence level",
    ],
    statusKey: "with_contacts" as const,
    statusLabel: "With contacts",
  },
];

function StageCard({
  stage,
  count,
  total,
}: {
  stage: (typeof STAGES)[number];
  count: number;
  total: number;
}) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;

  return (
    <div className="border border-neutral-200 bg-white">
      {/* Stage header */}
      <div className="flex items-start gap-4 px-6 py-5 border-b border-neutral-100">
        <span
          className="text-2xl font-light text-neutral-300 shrink-0"
          style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
        >
          {stage.number}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-lg font-medium">{stage.title}</h3>
            <span
              className="text-[10px] text-muted uppercase tracking-widest shrink-0 px-2 py-0.5 border border-neutral-200 rounded-full"
              style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
            >
              {stage.engine}
            </span>
          </div>
          <p className="text-sm text-muted font-light leading-relaxed mt-1.5">
            {stage.description}
          </p>
        </div>
      </div>

      {/* Inputs → Outputs */}
      <div className="grid sm:grid-cols-2 divide-x divide-neutral-100">
        <div className="px-6 py-4">
          <p
            className="text-[10px] font-medium text-muted uppercase tracking-widest mb-2"
            style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
          >
            Inputs
          </p>
          <ul className="space-y-1">
            {stage.inputs.map((item) => (
              <li key={item} className="text-xs text-muted font-light flex gap-2">
                <span className="text-neutral-300 shrink-0">&rarr;</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="px-6 py-4">
          <p
            className="text-[10px] font-medium text-muted uppercase tracking-widest mb-2"
            style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
          >
            Outputs
          </p>
          <ul className="space-y-1">
            {stage.outputs.map((item) => (
              <li key={item} className="text-xs text-muted font-light flex gap-2">
                <span className="text-emerald-500 shrink-0">&check;</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-6 py-3 border-t border-neutral-100 bg-neutral-50">
        <div className="flex items-center justify-between mb-1.5">
          <span
            className="text-[10px] text-muted uppercase tracking-widest"
            style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
          >
            {stage.statusLabel}
          </span>
          <span
            className="text-[10px] text-muted tabular-nums"
            style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
          >
            {count}/{total} ({pct}%)
          </span>
        </div>
        <div className="h-1 bg-neutral-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-neutral-900 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}

export default function PipelinePage() {
  const [status, setStatus] = useState<PipelineStatusResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getPipelineStatus()
      .then(setStatus)
      .catch(() => setError(true));
  }, []);

  const total = status?.total_contractors ?? 0;

  return (
    <div className="mx-auto max-w-4xl px-6 py-12 space-y-10">
      {/* Header */}
      <div>
        <p
          className="text-xs font-medium text-muted uppercase tracking-widest mb-3"
          style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
        >
          Enrichment Pipeline
        </p>
        <h1 className="text-4xl font-light text-foreground leading-tight">
          How leads get scored.
        </h1>
        <p className="text-muted font-light mt-3 max-w-2xl leading-relaxed">
          Each contractor passes through four stages. Structured data is scored
          deterministically. Unstructured research is analyzed by LLMs. The result
          is an actionable, explainable lead score with sales-ready intelligence.
        </p>
      </div>

      {/* Architecture flow */}
      <div className="border border-neutral-900 bg-[#171717] rounded-2xl px-6 py-5">
        <p
          className="text-[10px] font-medium text-neutral-500 uppercase tracking-widest mb-4"
          style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
        >
          Data Flow
        </p>
        <div className="flex items-center justify-between gap-2 overflow-x-auto">
          {[
            { label: "GAF Directory", sub: "Playwright" },
            { label: "Research", sub: "Perplexity" },
            { label: "Score & Analyze", sub: "Python + OpenAI" },
            { label: "Contacts", sub: "OpenAI" },
            { label: "Dashboard", sub: "Next.js" },
          ].map((step, i, arr) => (
            <div key={step.label} className="flex items-center gap-2 shrink-0">
              <div className="text-center">
                <p className="text-xs font-medium text-white">{step.label}</p>
                <p
                  className="text-[10px] text-neutral-500 mt-0.5"
                  style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
                >
                  {step.sub}
                </p>
              </div>
              {i < arr.length - 1 && (
                <svg className="h-4 w-4 text-neutral-600 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Scoring methodology */}
      <div className="border-l-2 border-neutral-900 pl-5 py-2">
        <h3
          className="text-xs font-medium text-muted uppercase tracking-widest mb-2"
          style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
        >
          Scoring Methodology
        </h3>
        <div className="grid sm:grid-cols-2 gap-4 mt-3">
          <div>
            <p
              className="text-[10px] font-medium text-muted uppercase tracking-widest mb-2"
              style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
            >
              Deterministic (60 pts)
            </p>
            <ul className="space-y-1.5">
              {[
                ["Certification Tier", "0\u201330 pts", "President's Club = 30, Master Elite = 25"],
                ["Review Volume", "0\u201320 pts", "Log-scaled from review count"],
                ["Rating Quality", "0\u201310 pts", "Star rating weighted by review confidence"],
              ].map(([name, pts, desc]) => (
                <li key={name} className="text-xs font-light">
                  <span className="font-medium">{name}</span>{" "}
                  <span className="text-muted">({pts})</span>
                  <br />
                  <span className="text-muted">{desc}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p
              className="text-[10px] font-medium text-muted uppercase tracking-widest mb-2"
              style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
            >
              LLM-Assessed (40 pts)
            </p>
            <ul className="space-y-1.5">
              {[
                ["Business Signals", "0\u201320 pts", "Growth, hiring, expansion from research"],
                ["Why Now Urgency", "0\u201320 pts", "Storms, seasonal demand, supplier issues"],
              ].map(([name, pts, desc]) => (
                <li key={name} className="text-xs font-light">
                  <span className="font-medium">{name}</span>{" "}
                  <span className="text-muted">({pts})</span>
                  <br />
                  <span className="text-muted">{desc}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Stage cards with live status */}
      <div>
        <p
          className="text-xs font-medium text-muted uppercase tracking-widest mb-4"
          style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
        >
          Pipeline Stages
        </p>

        {error && (
          <div className="border border-neutral-200 p-8 text-center mb-4">
            <p className="text-sm text-muted font-light">
              Could not connect to the backend. Start the API server to see live pipeline status.
            </p>
          </div>
        )}

        <div className="space-y-4">
          {STAGES.map((stage) => (
            <StageCard
              key={stage.number}
              stage={stage}
              count={status?.[stage.statusKey] ?? 0}
              total={total}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
