"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ExternalLink, Radar, RefreshCw, ShieldAlert, X } from "lucide-react";

import { TopNav } from "@/components/TopNav";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { api, queryKeys } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useCommandStore } from "@/store/useCommandStore";

const KIND_LABEL: Record<string, string> = {
  grap_stage: "GRAP stage",
  construction: "Construction",
  incident: "Incident",
};

/**
 * Evidence Scout review queue (Phase L3). The layers with no API — GRAP stage in
 * force, construction activity, incidents — found by a Bedrock model + web
 * search. Everything here is advisory and badged "web-scouted · unverified": an
 * LLM finding never becomes an order by itself. A human promotes or dismisses.
 */
export default function ScoutPage() {
  const cityId = useCommandStore((s) => s.cityId);
  const qc = useQueryClient();
  const cities = useQuery({ queryKey: queryKeys.cities, queryFn: api.cities });
  const q = useQuery({
    queryKey: queryKeys.scout(cityId, "pending"),
    queryFn: () => api.scout(cityId, "pending"),
    enabled: Boolean(cityId),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["scout"] });
  const run = useMutation({ mutationFn: () => api.scoutRun(cityId), onSuccess: invalidate });
  const promote = useMutation({ mutationFn: (id: string) => api.scoutPromote(id), onSuccess: invalidate });
  const dismiss = useMutation({ mutationFn: (id: string) => api.scoutDismiss(id), onSuccess: invalidate });

  const enabled = q.data?.enabled ?? false;
  const items = q.data?.items ?? [];

  return (
    <div className="flex h-dvh flex-col bg-base">
      <TopNav cities={cities.data ?? []} loading={cities.isLoading} />
      <main className="mx-auto w-full max-w-5xl flex-1 overflow-y-auto px-6 py-6">
        <header className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-xl font-semibold text-slate-100">
              <Radar className="h-5 w-5 text-data" aria-hidden />
              Evidence Scout
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-500">
              For the layers with no feed — the GRAP stage actually in force,
              construction dust, and incidents — a Bedrock model reads live web
              search results and proposes candidates. Everything is{" "}
              <span className="text-amber-400">advisory and unverified</span>{" "}
              until you promote it; it is never dispatched automatically.
            </p>
          </div>
          <button
            onClick={() => run.mutate()}
            disabled={run.isPending || !enabled}
            data-testid="scout-run"
            className="flex shrink-0 items-center gap-1.5 rounded-md border border-edge bg-surface-2 px-3 py-2 text-xs font-medium text-slate-100 transition-colors hover:border-data/50 disabled:opacity-50"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", run.isPending && "animate-spin")} aria-hidden />
            {run.isPending ? "Scouting…" : "Run sweep"}
          </button>
        </header>

        {!q.isPending && !enabled && (
          <div className="panel flex items-start gap-3 p-4">
            <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" aria-hidden />
            <div className="text-sm text-slate-300">
              <p className="font-medium text-slate-100">Scout is not configured</p>
              <p className="mt-1 text-slate-500">
                Set <code className="text-slate-300">BEDROCK_MODEL_ID</code> and a
                search provider (<code className="text-slate-300">SEARCH_PROVIDER</code>{" "}
                + key) in <code className="text-slate-300">.env</code> to enable
                live scouting. The review queue and guardrails work regardless.
              </p>
            </div>
          </div>
        )}

        {q.isPending && (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        )}

        {q.error && <ErrorState title="Could not load the scout queue" detail={(q.error as Error).message} onRetry={() => q.refetch()} />}

        {!q.isPending && enabled && items.length === 0 && (
          <EmptyState
            title="Nothing pending review"
            hint="Run a sweep to search for GRAP orders, construction activity and incidents."
          />
        )}

        <ul className="space-y-3">
          {items.map((it) => (
            <li key={it.id} className="panel p-4" data-testid={`scout-item-${it.id}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="rounded bg-data/15 px-1.5 py-0.5 text-[10px] font-medium text-data">
                      {KIND_LABEL[it.kind] ?? it.kind}
                    </span>
                    <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-400">
                      {it.badge}
                    </span>
                    <span className="numeral text-[10px] text-slate-500">
                      conf {(it.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="truncate text-sm font-medium text-slate-100">{it.title}</p>
                  <p className="mt-0.5 text-xs text-slate-400">{it.summary}</p>
                  {it.source_url && (
                    <a
                      href={it.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-data"
                    >
                      <ExternalLink className="h-3 w-3" aria-hidden />
                      {it.source_name || it.source_url}
                    </a>
                  )}
                </div>
                <div className="flex shrink-0 gap-1.5">
                  <button
                    onClick={() => promote.mutate(it.id)}
                    title="Promote — accept as corroborating evidence"
                    className="flex items-center gap-1 rounded border border-verified/30 bg-verified/10 px-2 py-1 text-xs font-medium text-verified transition-colors hover:bg-verified/20"
                  >
                    <Check className="h-3 w-3" aria-hidden /> Promote
                  </button>
                  <button
                    onClick={() => dismiss.mutate(it.id)}
                    title="Dismiss"
                    className="flex items-center gap-1 rounded border border-edge px-2 py-1 text-xs font-medium text-slate-400 transition-colors hover:bg-surface-2"
                  >
                    <X className="h-3 w-3" aria-hidden /> Dismiss
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}
