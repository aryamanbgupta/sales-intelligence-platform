"use client";

import type { LeadListItem, PaginationMeta } from "@/lib/types";
import { SORT_OPTIONS } from "@/lib/constants";
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
      className="text-xs font-medium text-muted hover:text-foreground transition-colors cursor-pointer flex items-center gap-0.5"
    >
      {label}
      {active && (
        <span className="text-foreground">
          {currentOrder === "desc" ? " \u2193" : " \u2191"}
        </span>
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
    <div className="bg-card rounded-lg border border-border shadow-sm overflow-hidden">
      {/* Table header */}
      <div className="grid grid-cols-[60px_1fr_150px_140px_70px] items-center gap-4 px-5 py-3 border-b border-border bg-slate-50/50">
        <SortHeader label="Score" column="lead_score" currentSort={sortBy} currentOrder={sortOrder} onSort={onSort} />
        <SortHeader label="Contractor" column="name" currentSort={sortBy} currentOrder={sortOrder} onSort={onSort} />
        <span className="text-xs font-medium text-muted">Certification</span>
        <SortHeader label="Rating" column="rating" currentSort={sortBy} currentOrder={sortOrder} onSort={onSort} />
        <SortHeader label="Dist" column="distance_miles" currentSort={sortBy} currentOrder={sortOrder} onSort={onSort} />
      </div>

      {/* Rows */}
      {loading ? (
        <div className="py-12 text-center text-sm text-muted">Loading leads...</div>
      ) : leads.length === 0 ? (
        <div className="py-12 text-center text-sm text-muted">
          No leads match your filters.
        </div>
      ) : (
        leads.map((lead) => <LeadRow key={lead.id} lead={lead} />)
      )}

      {/* Pagination */}
      {pagination.total_pages > 1 && (
        <div className="flex items-center justify-between px-5 py-3 border-t border-border bg-slate-50/50">
          <span className="text-xs text-muted">
            {pagination.total_items} leads &middot; Page {pagination.page} of{" "}
            {pagination.total_pages}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="px-2.5 py-1 text-xs rounded border border-border bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors"
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
                  <span key={`ellipsis-${i}`} className="px-1 text-xs text-muted">
                    ...
                  </span>
                ) : (
                  <button
                    key={p}
                    onClick={() => onPageChange(p as number)}
                    className={`px-2.5 py-1 text-xs rounded border transition-colors cursor-pointer ${
                      p === pagination.page
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-white border-border hover:bg-slate-50"
                    }`}
                  >
                    {p}
                  </button>
                )
              )}
            <button
              onClick={() => onPageChange(pagination.page + 1)}
              disabled={pagination.page >= pagination.total_pages}
              className="px-2.5 py-1 text-xs rounded border border-border bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
