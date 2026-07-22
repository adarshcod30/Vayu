import type {
  Attribution,
  AuditList,
  Evaluation,
  Candidate,
  City,
  Current,
  Explain,
  Forecast,
  GrapState,
  HazardAlert,
  Health,
  Leaderboard,
  Order,
  OrderList,
  CitizenBrief,
  OrderStatus,
  TrajectoryCollection,
  VerificationList,
  WardCollection,
} from "./types";

/**
 * Requests go to a same-origin /api/v1 path, which next.config.mjs rewrites to
 * the API. One origin => no CORS preflight on the hot path.
 */
const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers: { Accept: "application/json" } });
  } catch (e) {
    // Network/offline: distinguish from an API that answered with an error, so
    // the ErrorState can say something true about what went wrong.
    throw new ApiError("Cannot reach the VAYU API", 0, e instanceof Error ? e.message : undefined);
  }

  if (!res.ok) {
    // The API speaks RFC7807; surface its `detail` rather than a bare status.
    let detail: string | undefined;
    try {
      const problem = await res.json();
      detail = problem?.detail ?? problem?.title;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail ?? `Request failed (${res.status})`, res.status, detail);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new ApiError("Cannot reach the VAYU API", 0, e instanceof Error ? e.message : undefined);
  }
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const problem = await res.json();
      detail = problem?.detail ?? problem?.title;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail ?? `Request failed (${res.status})`, res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<Health>("/health"),
  cities: () => get<City[]>("/cities"),
  current: (cityId: string) => get<Current>(`/cities/${cityId}/current`),
  wards: (cityId: string) => get<WardCollection>(`/cities/${cityId}/wards.geojson`),
  forecast: (cityId: string, h: number) => get<Forecast>(`/cities/${cityId}/forecast?h=${h}`),
  alerts: (cityId: string) => get<HazardAlert[]>(`/cities/${cityId}/alerts`),
  explain: (cityId: string, wardId: string, h: number) =>
    get<Explain>(`/cities/${cityId}/forecast/explain/${encodeURIComponent(wardId)}?h=${h}`),
  attribution: (cityId: string, wardId: string, hours: number) =>
    get<Attribution>(`/cities/${cityId}/attribution/${encodeURIComponent(wardId)}?hours=${hours}`),
  trajectory: (cityId: string, wardId: string, hours: number) =>
    get<TrajectoryCollection>(`/cities/${cityId}/trajectory/${encodeURIComponent(wardId)}?hours=${hours}`),

  interventions: (cityId: string, wardId?: string | null, actionType?: string | null) => {
    const q = new URLSearchParams();
    if (wardId) q.set("ward_id", wardId);
    if (actionType) q.set("action_type", actionType);
    const qs = q.toString();
    return get<Leaderboard>(`/cities/${cityId}/interventions${qs ? `?${qs}` : ""}`);
  },

  /** Renders the dossier and creates the order. The only write on this path —
   *  everything before it is a recommendation, this is a record. */
  dispatch: (candidate: Candidate, signalTs?: string) =>
    post<Order>("/interventions/dispatch", { candidate, signal_ts: signalTs ?? null }),

  orders: (cityId?: string, status?: OrderStatus) => {
    const q = new URLSearchParams();
    if (cityId) q.set("city_id", cityId);
    if (status) q.set("status", status);
    const qs = q.toString();
    return get<OrderList>(`/interventions${qs ? `?${qs}` : ""}`);
  },

  order: (orderId: string) => get<Order>(`/interventions/${encodeURIComponent(orderId)}`),

  execute: (orderId: string, note: string) =>
    post<Order>(`/interventions/${encodeURIComponent(orderId)}/execute`, { note }),

  dossierUrl: (orderId: string) => `${BASE}/interventions/${encodeURIComponent(orderId)}/dossier`,

  verifications: (cityId?: string) =>
    get<VerificationList>(`/verifications${cityId ? `?city_id=${cityId}` : ""}`),

  audit: (limit = 100) => get<AuditList>(`/audit?limit=${limit}`),
  evaluation: () => get<Evaluation>(`/meta/evaluation`),

  grap: (cityId: string) => get<GrapState>(`/cities/${cityId}/grap`),
  grapApprove: (draftId: string) => post<{ id: string; status: string }>(`/grap/${encodeURIComponent(draftId)}/approve`, {}),
  grapDismiss: (draftId: string) => post<{ id: string; status: string }>(`/grap/${encodeURIComponent(draftId)}/dismiss`, {}),
  auditStreamUrl: () => `${BASE}/audit/stream`,

  citizen: (cityId: string, wardId: string | null, lang: string) =>
    get<CitizenBrief>(
      wardId
        ? `/cities/${cityId}/citizen/${encodeURIComponent(wardId)}?lang=${lang}`
        : `/cities/${cityId}/citizen?lang=${lang}`,
    ),

  clock: () => get<Clock>("/clock"),
  demoDates: (cityId: string) => get<{ city: string; dates: DemoDate[] }>(`/demo-dates?city_id=${cityId}`),
  /** Pin the app clock to an instant (ISO), or null to return to demo/live. */
  setClock: (asOf: string | null) => post<Clock>("/clock", { as_of: asOf }),
  /** Flip demo/live at runtime. demo_mode=false → live wall clock + a background
   *  gap-fill for `cityId` (CPCB/OpenAQ + weather + fires + scout) for TODAY. */
  setMode: (demoMode: boolean, cityId = "delhi") =>
    post<Clock>("/mode", { demo_mode: demoMode, city_id: cityId }),

  scout: (cityId?: string, status = "pending") => {
    const q = new URLSearchParams({ status });
    if (cityId) q.set("city_id", cityId);
    return get<ScoutList>(`/scout?${q.toString()}`);
  },
  scoutRun: (cityId: string) => post<ScoutRun>(`/scout/run?city_id=${cityId}`, {}),
  scoutPromote: (id: string) => post<{ id: string; status: string }>(`/scout/${encodeURIComponent(id)}/promote`, {}),
  scoutDismiss: (id: string) => post<{ id: string; status: string }>(`/scout/${encodeURIComponent(id)}/dismiss`, {}),
};

export interface ScoutItem {
  id: string;
  city: string;
  kind: "grap_stage" | "construction" | "incident";
  title: string;
  summary: string;
  lat: number | null;
  lon: number | null;
  source_url: string;
  source_name: string;
  published: string;
  scouted_ts: string | null;
  model: string;
  confidence: number;
  status: string;
  badge: string;
}
export interface ScoutList {
  enabled: boolean;
  items: ScoutItem[];
  count: number;
}
export interface ScoutRun {
  enabled: boolean;
  reason: string;
  found: number;
  written: number;
  by_kind: Record<string, number>;
}

export interface Clock {
  now: string;
  demo_mode: boolean;
  source: "override" | "demo" | "live";
  live: boolean;
  pinned: boolean;
  data_min: string | null;
  data_max: string | null;
  max_selectable: string | null;
  /** Cities with a live gap-fill in flight; poll until empty, then refetch. */
  filling?: string[];
}

/** A curated, pre-scored Demo-mode episode — see meta.py:DEMO_DATES. */
export interface DemoDate {
  at: string;
  label: string;
  aqi: number;
  category: string;
}

export const queryKeys = {
  health: ["health"] as const,
  clock: ["clock"] as const,
  demoDates: (cityId: string) => ["demoDates", cityId] as const,
  scout: (cityId: string, status: string) => ["scout", cityId, status] as const,
  cities: ["cities"] as const,
  current: (cityId: string) => ["current", cityId] as const,
  wards: (cityId: string) => ["wards", cityId] as const,
  forecast: (cityId: string, h: number) => ["forecast", cityId, h] as const,
  alerts: (cityId: string) => ["alerts", cityId] as const,
  explain: (cityId: string, wardId: string, h: number) => ["explain", cityId, wardId, h] as const,
  attribution: (cityId: string, wardId: string, hours: number) =>
    ["attribution", cityId, wardId, hours] as const,
  trajectory: (cityId: string, wardId: string, hours: number) =>
    ["trajectory", cityId, wardId, hours] as const,
  interventions: (cityId: string, wardId?: string | null, actionType?: string | null) =>
    ["interventions", cityId, wardId ?? null, actionType ?? null] as const,
  orders: (cityId?: string, status?: string) => ["orders", cityId ?? null, status ?? null] as const,
  order: (orderId: string) => ["order", orderId] as const,
  verifications: (cityId?: string) => ["verifications", cityId ?? null] as const,
  citizen: (cityId: string, wardId: string | null, lang: string) =>
    ["citizen", cityId, wardId ?? null, lang] as const,
  audit: ["audit"] as const,
  evaluation: ["evaluation"] as const,
  grap: (cityId: string) => ["grap", cityId] as const,
};
