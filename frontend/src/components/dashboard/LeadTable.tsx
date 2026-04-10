"use client";

import type { LeadListItem, PaginationMeta } from "@/lib/types";
import LeadRow from "./LeadRow";

interface LeadTableProps {
  leads: LeadListItem[];
  pagination: PaginationMeta;
  sortBy: string;
  sortOrder: string;
  onSort: (column: string) => void;
  onPageChange: (page: number) => void;
  loading: boolean;
}

function SortHeader({
  label,
  column,
  currentSort,
  currentOrder,
  onSort,
}: {
  label: string;
  column: string;
  currentSort: string;
  currentOrder: string;
  onSort: (col: string) => void;
}) {
  const active = currentSort === column;
  return (
    <button
      onClick={() => onSort(column)}
      className={`text-xs font-medium uppercase tracking-widest transition-colors cursor-pointer flex items-center gap-0.5 ${
        active ? "text-neutral-900" : "text-neutral-500 hover:text-neutral-900"
      }`}
      style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
    >
      {label}
      {active && (
        <span>{currentOrder === "desc" ? " \u2193" : " \u2191"}</span>
      )}
    </button>
  );
}

export default function LeadTable({
  leads,
  pagination,
  sortBy,
  sortOrder,
  onSort,
  onPageChange,
  loading,
}: LeadTableProps) {
  return (
    <div className="border border-neutral-200 overflow-hidden">
      {/* Table header */}
      <div className="grid grid-cols-[56px_1fr_120px_72px] items-center gap-4 px-5 py-3 border-b border-neutral-900 bg-neutral-50">
        <SortHeader label="Score" column="lead_score" currentSort={sortBy} currentOrder={sortOrder} onSort={onSort} />
        <SortHeader label="Contractor" column="name" currentSort={sortBy} currentOrder={sortOrder} onSort={onSort} />
        <SortHeader label="Est. Volume" column="review_count" currentSort={sortBy} currentOrder={sortOrder} onSort={onSort} />
        <SortHeader label="Dist" column="distance_miles" currentSort={sortBy} currentOrder={sortOrder} onSort={onSort} />
      </div>

      {/* Rows */}
      <div className="bg-white">
        {loading ? (
          <div className="py-16 text-center text-sm text-muted">Loading leads...</div>
        ) : leads.length === 0 ? (
          <div className="py-16 text-center text-sm text-muted">
            No leads match your filters.
          </div>
        ) : (
          leads.map((lead) => <LeadRow key={lead.id} lead={lead} />)
        )}
      </div>

      {/* Pagination */}
      {pagination.total_pages > 1 && (
        <div className="flex items-center justify-between px-5 py-3 border-t border-neutral-900 bg-neutral-50">
          <span
            className="text-xs text-muted tracking-wide"
            style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
          >
            {pagination.total_items} leads &middot; Page {pagination.page}/{pagination.total_pages}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="px-3 py-1 text-xs rounded-full border border-neutral-300 bg-white hover:border-neutral-900 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-colors"
              style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
            >
              Prev
            </button>
            {Array.from({ length: pagination.total_pages }, (_, i) => i + 1)
              .filter(
                (p) =>
                  p === 1 ||
                  p === pagination.total_pages ||
                  Math.abs(p - pagination.page) <= 1
              )
              .reduce<(number | "...")[]>((acc, p, i, arr) => {
                if (i > 0 && p - (arr[i - 1] as number) > 1) acc.push("...");
                acc.push(p);
                return acc;
              }, [])
              .map((p, i) =>
                p === "..." ? (
                  <span key={`ellipsis-${i}`} className="px-1.5 text-xs text-muted">
                    ...
                  </span>
                ) : (
                  <button
                    key={p}
                    onClick={() => onPageChange(p as number)}
                    className={`px-3 py-1 text-xs rounded-full border transition-colors cursor-pointer ${
                      p === pagination.page
                        ? "bg-neutral-900 text-white border-neutral-900"
                        : "bg-white border-neutral-300 hover:border-neutral-900"
                    }`}
                    style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
                  >
                    {p}
                  </button>
                )
              )}
            <button
              onClick={() => onPageChange(pagination.page + 1)}
              disabled={pagination.page >= pagination.total_pages}
              className="px-3 py-1 text-xs rounded-full border border-neutral-300 bg-white hover:border-neutral-900 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-colors"
              style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
