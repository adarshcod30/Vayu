"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  Clock as ClockIcon,
  FastForward,
  Radio,
  RotateCcw,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api, queryKeys } from "@/lib/api";
import { aqiColor, readableOn } from "@/lib/aqi";
import { cn } from "@/lib/cn";
import { useCommandStore } from "@/store/useCommandStore";

const HOUR_MS = 3_600_000;
const DAY_MS = 86_400_000;
const IST_OFFSET_MIN = 330; // +5:30

/** ISO instant → IST date ("YYYY-MM-DD") and time ("HH:mm") strings.
 *
 * getTime() is epoch-UTC (browser-tz-independent); adding the fixed +5:30 and
 * then reading UTC components via toISOString() yields IST wall time in ANY
 * browser. (Using getTimezoneOffset() here was a bug: in an IST browser it
 * cancelled the offset, so the picker showed UTC and capped a day early.) */
function istParts(iso: string): { date: string; time: string } {
  const ist = new Date(new Date(iso).getTime() + IST_OFFSET_MIN * 60000);
  const s = ist.toISOString();
  return { date: s.slice(0, 10), time: s.slice(11, 16) };
}

/** IST date + time (wall clock) → UTC ISO the API can pin to. */
function combineIst(date: string, time: string): string {
  const asUtcMs = new Date(`${date}T${time}:00Z`).getTime() - IST_OFFSET_MIN * 60000;
  return new Date(asUtcMs).toISOString();
}

function clampIso(iso: string, min?: string | null, max?: string | null): string {
  let t = new Date(iso).getTime();
  if (min) t = Math.max(t, new Date(min).getTime());
  if (max) t = Math.min(t, new Date(max).getTime());
  return new Date(t).toISOString();
}

/**
 * Live clock + time-travel control (L1b). Shows the app's current instant and a
 * live / demo / pinned badge; lets the operator move to any hour the data covers
 * — via a date+time picker or day/hour steppers — and snaps everything (nowcast,
 * forecast, alerts, GRAP, ROI) to it. When live, the shown time ticks each
 * second; the server clock is polled every 60 s.
 */
export function ClockControl() {
  const qc = useQueryClient();
  const cityId = useCommandStore((s) => s.cityId);
  // Poll fast while a live gap-fill is running so the whole app refreshes the
  // moment today's data lands; otherwise a lazy 60 s heartbeat.
  const clock = useQuery({
    queryKey: queryKeys.clock,
    queryFn: api.clock,
    refetchInterval: (q) => ((q.state.data?.filling?.length ?? 0) > 0 ? 4_000 : 60_000),
    // Keep polling even when the tab is backgrounded — a user who switches
    // away during the live fetch must find the page refreshed when they return.
    refetchIntervalInBackground: true,
  });
  const demoDates = useQuery({
    queryKey: queryKeys.demoDates(cityId),
    queryFn: () => api.demoDates(cityId),
    staleTime: Infinity, // curated server-side; doesn't change under a running app
  });
  const [open, setOpen] = useState(false);
  const [, setTick] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  const source = clock.data?.source ?? "demo";
  const live = source === "live";
  const demoMode = clock.data?.demo_mode ?? true;
  const dataMin = clock.data?.data_min ?? null;
  const dataMax = clock.data?.data_max ?? null;
  const maxSelectable = clock.data?.max_selectable ?? dataMax;
  const nowIso = clock.data?.now ?? null;
  const fillingNow = (clock.data?.filling?.length ?? 0) > 0;

  // When the gap-fill finishes (filling → empty), refetch every surface: the
  // nowcast, forecast, alerts, attribution all just changed under us.
  const wasFilling = useRef(false);
  useEffect(() => {
    if (wasFilling.current && !fillingNow) qc.invalidateQueries();
    wasFilling.current = fillingNow;
  }, [fillingNow, qc]);

  useEffect(() => {
    if (!live) return;
    const t = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [live]);

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onEsc);
    };
  }, []);

  const setClock = useMutation({
    mutationFn: (asOf: string | null) => api.setClock(asOf),
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.clock, data);
      qc.invalidateQueries(); // "now" drives every read; refresh all of it
    },
  });

  const setMode = useMutation({
    mutationFn: (demo: boolean) => api.setMode(demo, cityId),
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.clock, data);
      qc.invalidateQueries();
    },
  });

  const pinTo = (iso: string) => setClock.mutate(clampIso(iso, dataMin, maxSelectable));
  const shift = (ms: number) => {
    if (!nowIso) return;
    pinTo(new Date(new Date(nowIso).getTime() + ms).toISOString());
  };

  const shown = live ? new Date() : nowIso ? new Date(nowIso) : null;
  const label = shown
    ? shown.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" })
    : "—";
  const parts = nowIso ? istParts(nowIso) : { date: "", time: "" };
  const badge =
    source === "live"
      ? { text: "live", cls: "text-verified" }
      : source === "override"
        ? { text: "pinned", cls: "text-amber-400" }
        : { text: "demo", cls: "text-slate-500" };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        data-testid="clock-control"
        title="App clock — click to time-travel"
        className={cn(
          "flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors",
          source === "override"
            ? "border-amber-500/40 bg-amber-500/10 text-amber-200"
            : "border-edge bg-surface-2 text-slate-200 hover:border-data/50",
        )}
      >
        {live ? (
          <Radio className="h-3 w-3 shrink-0 text-verified" aria-hidden />
        ) : (
          <ClockIcon className="h-3 w-3 shrink-0 text-slate-400" aria-hidden />
        )}
        <span className="numeral whitespace-nowrap">{label}</span>
        <span className={cn("whitespace-nowrap text-[9px] uppercase tracking-wider", badge.cls)}>
          IST · {badge.text}
        </span>
        {fillingNow && (
          <span className="flex items-center gap-1 whitespace-nowrap text-[9px] uppercase tracking-wider text-data">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-data" aria-hidden />
            fetching
          </span>
        )}
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1.5 w-[300px] rounded-md border border-edge bg-surface p-3 shadow-2xl">
          {/* Demo / Live mode toggle. Live = wall clock + live feeds for today;
              Demo = bundled past data pinned to the demo date. */}
          <div className="mb-3">
            <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-500">Mode</p>
            <div className="flex rounded-md border border-edge bg-surface-2 p-0.5" role="tablist">
              <button
                role="tab"
                aria-selected={demoMode}
                data-testid="mode-demo"
                onClick={() => !demoMode && setMode.mutate(true)}
                disabled={setMode.isPending}
                className={cn(
                  "flex-1 rounded px-2 py-1 text-[11px] font-medium transition-colors",
                  demoMode ? "bg-data/15 text-data" : "text-slate-400 hover:text-slate-200",
                )}
              >
                Demo · sample
              </button>
              <button
                role="tab"
                aria-selected={!demoMode}
                data-testid="mode-live"
                onClick={() => demoMode && setMode.mutate(false)}
                disabled={setMode.isPending}
                className={cn(
                  "flex-1 rounded px-2 py-1 text-[11px] font-medium transition-colors",
                  !demoMode ? "bg-verified/15 text-verified" : "text-slate-400 hover:text-slate-200",
                )}
              >
                {setMode.isPending ? "…" : "Live · today"}
              </button>
            </div>
            <p className="mt-1 text-[10px] leading-relaxed text-slate-500">
              {demoMode
                ? "Bundled data, clock pinned — deterministic for the demo."
                : fillingNow
                  ? "Fetching today's live data — CPCB, OpenAQ, weather, fires, web scout. The page refreshes itself when it lands (a few minutes)."
                  : "Live feeds + wall clock for the present day."}
            </p>
          </div>

          {demoMode && (demoDates.data?.dates?.length ?? 0) > 0 && (
            <div className="mb-3">
              <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-slate-500">
                Demo episodes — pre-scored
              </p>
              <ul className="space-y-1">
                {(demoDates.data?.dates ?? []).map((d) => {
                  const selected = nowIso && new Date(nowIso).getTime() === new Date(d.at).getTime();
                  const color = aqiColor(d.aqi);
                  return (
                    <li key={d.at}>
                      <button
                        onClick={() => pinTo(d.at)}
                        disabled={setClock.isPending}
                        data-testid={`demo-date-${d.at}`}
                        className={cn(
                          "flex w-full items-center justify-between gap-2 rounded border px-2 py-1.5 text-left transition-colors disabled:opacity-50",
                          selected ? "border-data/50 bg-data/10" : "border-edge bg-surface-2 hover:border-data/40",
                        )}
                      >
                        <span className="min-w-0">
                          <span className="block truncate text-xs font-medium text-slate-100">{d.label}</span>
                          <span className="numeral block text-[10px] text-slate-500">
                            {new Date(d.at).toLocaleDateString("en-IN", {
                              day: "numeric",
                              month: "short",
                              year: "numeric",
                              timeZone: "Asia/Kolkata",
                            })}
                          </span>
                        </span>
                        <span
                          className="numeral shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold"
                          style={{ background: color, color: readableOn(color) }}
                        >
                          {d.aqi}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          <div>
            <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-slate-500">
              Time-travel the airshed
            </p>

            {/* Date + time selection (IST). Bounded to the data coverage window. */}
            <div className="flex gap-2">
              <label className="flex-1">
                <span className="mb-1 block text-[9px] uppercase tracking-wider text-slate-500">Date</span>
                <input
                  type="date"
                  data-testid="clock-date"
                  value={parts.date}
                  min={dataMin ? istParts(dataMin).date : undefined}
                  max={maxSelectable ? istParts(maxSelectable).date : undefined}
                  onChange={(e) => e.target.value && pinTo(combineIst(e.target.value, parts.time || "06:00"))}
                  className="w-full rounded border border-edge bg-surface-2 px-2 py-1.5 text-xs text-slate-100"
                />
              </label>
              <label className="w-24">
                <span className="mb-1 block text-[9px] uppercase tracking-wider text-slate-500">Time</span>
                <input
                  type="time"
                  data-testid="clock-time"
                  value={parts.time}
                  onChange={(e) => e.target.value && pinTo(combineIst(parts.date, e.target.value))}
                  className="w-full rounded border border-edge bg-surface-2 px-2 py-1.5 text-xs text-slate-100"
                />
              </label>
            </div>

            {/* Steppers — the easy way to walk through the dates in between. */}
            <div className="mt-2 grid grid-cols-4 gap-1.5">
              <StepBtn onClick={() => shift(-DAY_MS)} label="−1 day">
                <ChevronLeft className="h-3 w-3" aria-hidden />
                1d
              </StepBtn>
              <StepBtn onClick={() => shift(-HOUR_MS)} label="−1 hour">
                <ChevronLeft className="h-3 w-3" aria-hidden />
                1h
              </StepBtn>
              <StepBtn onClick={() => shift(HOUR_MS)} label="+1 hour">
                1h
                <ChevronRight className="h-3 w-3" aria-hidden />
              </StepBtn>
              <StepBtn onClick={() => shift(DAY_MS)} label="+1 day">
                1d
                <ChevronRight className="h-3 w-3" aria-hidden />
              </StepBtn>
            </div>

            <p className="mt-2 text-[10px] leading-relaxed text-slate-500">
              Snaps the nowcast, forecast, alerts, GRAP stage and ROI to that hour. Forecasts are scored on demand.
            </p>

            {dataMax && (
              <button
                onClick={() => pinTo(dataMax)}
                disabled={setClock.isPending}
                data-testid="clock-latest"
                className="mt-2 flex w-full items-center justify-center gap-1.5 rounded border border-edge bg-surface-2 px-2 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:border-data/50 disabled:opacity-50"
              >
                <FastForward className="h-3 w-3" aria-hidden />
                Latest data
              </button>
            )}
          </div>

          <button
            onClick={() => setClock.mutate(null)}
            disabled={setClock.isPending}
            data-testid="clock-reset"
            title={live ? "Return to live wall clock" : "Return to the demo date"}
            className="mt-1.5 flex w-full items-center justify-center gap-1.5 rounded border border-edge bg-surface-2 px-2 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:border-data/50 disabled:opacity-50"
          >
            <RotateCcw className="h-3 w-3" aria-hidden />
            {setClock.isPending ? "…" : live ? "Live now" : "Demo date"}
          </button>
        </div>
      )}
    </div>
  );
}

function StepBtn({
  onClick,
  label,
  children,
}: {
  onClick: () => void;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className="flex items-center justify-center gap-0.5 rounded border border-edge bg-surface-2 px-1 py-1.5 text-[11px] font-medium text-slate-300 transition-colors hover:border-data/50 hover:text-slate-100"
    >
      {children}
    </button>
  );
}
