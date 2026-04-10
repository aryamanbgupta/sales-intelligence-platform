"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getLeads, getStats } from "@/lib/api";
import type { LeadListItem, PaginationMeta, StatsResponse } from "@/lib/types";
import { SCORE_TIERS } from "@/lib/constants";
import StatsBar from "@/components/dashboard/StatsBar";
import FilterBar from "@/components/dashboard/FilterBar";
import LeadTable from "@/components/dashboard/LeadTable";

function tierToScoreRange(tier: string): { min_score?: number; max_score?: number } {
  switch (tier) {
    case "hot":
      return { min_score: SCORE_TIERS.HOT.min };
    case "warm":
      return { min_score: SCORE_TIERS.WARM.min, max_score: SCORE_TIERS.HOT.min - 1 };
    case "cold":
      return { max_score: SCORE_TIERS.WARM.min - 1 };
    default:
      return {};
  }
}

function Dashboard() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Read initial state from URL
  const initialPage = Number(searchParams.get("page")) || 1;
  const initialSortBy = searchParams.get("sort_by") || "lead_score";
  const initialSortOrder = searchParams.get("sort_order") || "desc";
  const initialTier = searchParams.get("tier") || "";
  const initialCert = searchParams.get("certification") || "";
  const initialSearch = searchParams.get("search") || "";

  const [leads, setLeads] = useState<LeadListItem[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta>({
    page: initialPage,
    per_page: 20,
    total_items: 0,
    total_pages: 0,
  });
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const [page, setPage] = useState(initialPage);
  const [sortBy, setSortBy] = useState(initialSortBy);
  const [sortOrder, setSortOrder] = useState(initialSortOrder);
  const [scoreTier, setScoreTier] = useState(initialTier);
  const [certification, setCertification] = useState(initialCert);
  const [search, setSearch] = useState(initialSearch);

  // Debounced search input
  const [searchInput, setSearchInput] = useState(initialSearch);

  // Sync state to URL
  const syncUrl = useCallback(
    (params: Record<string, string | number>) => {
      const sp = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== "" && v !== undefined && v !== null) {
          sp.set(k, String(v));
        }
      });
      const qs = sp.toString();
      router.replace(qs ? `/?${qs}` : "/", { scroll: false });
    },
    [router]
  );

  // Fetch leads whenever filters change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const scoreRange = tierToScoreRange(scoreTier);
    const params = {
      page,
      per_page: 20,
      sort_by: sortBy,
      sort_order: sortOrder,
      ...scoreRange,
      certification: certification || undefined,
      search: search || undefined,
    };

    getLeads(params)
      .then((res) => {
        if (cancelled) return;
        setLeads(res.data);
        setPagination(res.pagination);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setLoading(false);
      });

    syncUrl({
      page,
      sort_by: sortBy,
      sort_order: sortOrder,
      tier: scoreTier,
      certification,
      search,
    });

    return () => {
      cancelled = true;
    };
  }, [page, sortBy, sortOrder, scoreTier, certification, search, syncUrl]);

  // Fetch stats once on mount
  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, []);

  // Debounce search input → actual search
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  function handleSort(column: string) {
    if (sortBy === column) {
      setSortOrder((o) => (o === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(column);
      setSortOrder("desc");
    }
    setPage(1);
  }

  function handleScoreTierChange(tier: string) {
    setScoreTier(tier);
    setPage(1);
  }

  function handleCertChange(cert: string) {
    setCertification(cert);
    setPage(1);
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
      <StatsBar stats={stats} />

      <FilterBar
        scoreTier={scoreTier}
        certification={certification}
        search={searchInput}
        onScoreTierChange={handleScoreTierChange}
        onCertificationChange={handleCertChange}
        onSearchChange={setSearchInput}
      />

      <LeadTable
        leads={leads}
        pagination={pagination}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onSort={handleSort}
        onPageChange={setPage}
        loading={loading}
      />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-6 py-8 text-sm text-muted">Loading...</div>}>
      <Dashboard />
    </Suspense>
  );
}
