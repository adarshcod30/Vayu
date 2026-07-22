# VAYU — deployment

Ships **code only**. The hot DuckDB (seeded demo state + model artifacts) lives
in S3; the API pulls it on boot (`vayu_core/storage.py`, called from the
FastAPI lifespan) — this is what lets the container image stay small and the
same mechanism work under either hosting path below.

---

## Fast path (used for the hackathon deploy): Render + Vercel

**Why not AWS App Runner/Fargate directly:** checked the IAM user's actual
permissions (not just what was requested) — it has S3 + Bedrock but **not**
ECR, App Runner, ECS, or EventBridge, and granting those needs
`iam:PassRole`, which usually needs AWS account-admin access, not just a
policy attach. Rather than risk that close to a deadline, the API runs on
**Render** (Docker-native, needs zero extra AWS permissions — it only ever
calls S3/Bedrock at *runtime*, which already works) and the web on **Vercel**
(built for Next.js). Total new setup: two free accounts, no AWS console work.

```
 GitHub repo (code only, no data/*.duckdb — 100MB hard limit)
      │                                    │
      ▼ connect                            ▼ connect
 ┌─────────────┐  pulls hot DB   ┌────────────────┐
 │ Render       │◀───────────────│  S3 bucket      │
 │ vayu-api      │   on boot      │  hot/vayu.duckdb│
 │ (Dockerfile)  │─── Bedrock/Tavily on live-toggle click
 └──────┬────────┘
        │ same-origin proxy (Next.js rewrites, no CORS needed)
 ┌──────▼────────┐
 │ Vercel         │
 │ apps/web        │  ← what judges open
 └────────────────┘
```

### 1. Push the repo to GitHub (data files are gitignored — DB stays in S3)

```bash
git init                                    # if not already a repo
git add -A
git commit -m "VAYU"
# create an empty repo at github.com/new, then:
git remote add origin https://github.com/<you>/vayu.git
git branch -M main
git push -u origin main
```

### 2. Make sure S3 has the current seed (source of truth for Render)

```bash
make seed        # only if you want to reseed; skip if data/vayu.duckdb is current
python -c "from vayu_core.storage import push_hot_db; push_hot_db()"
```

### 3. Deploy the API — Render

1. render.com → **New → Blueprint** → connect the GitHub repo. Render reads
   [`render.yaml`](../render.yaml) at the repo root and creates `vayu-api`
   from `deploy/Dockerfile.api` automatically.
2. It will prompt for the `sync: false` secrets — open your local `.env` and
   paste in: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `TAVILY_API_KEY`,
   `DATA_GOV_IN_API_KEY`, `OPENAQ_API_KEY`, `FIRMS_API_KEY`.
3. Deploy. Render gives a URL like `https://vayu-api.onrender.com` — confirm
   `https://vayu-api.onrender.com/api/v1/health` returns `{"status":"ok",...}`.
4. **Free tier sleeps after 15 min idle** (a judge's first click eats a
   30–50s cold start) and its RAM is tight for pandas+LightGBM+DuckDB under
   load. `render.yaml` defaults to the **Starter** plan (a few $/mo, no
   sleep) — worth it for the judging window; you can downgrade after.

### 4. Deploy the web — Vercel

1. vercel.com → **Add New → Project** → import the same GitHub repo.
2. **Root Directory** → `apps/web` (Vercel auto-detects Next.js from there).
3. Add environment variable `NEXT_PUBLIC_API_URL` = the Render URL from step 3
   (no trailing slash). This is consumed server-side by
   [`next.config.js`](../apps/web/next.config.js)'s `rewrites()`, which proxies
   `/api/v1/*` to it — the browser only ever talks to the Vercel domain, so
   **no CORS setup is needed**.
4. Deploy. Vercel gives the public URL — this is the one you send judges.
5. Any future `git push` to `main` auto-redeploys both services.

### 5. Verify end-to-end

Open the Vercel URL → should load the Command Center pinned to the demo
episode (3 Nov 2025, AQI 373). Click the clock chip → **Live · today** →
watch it fetch CPCB/OpenAQ/weather/FIRMS/scout for the real present day and
refresh itself. Toggle back to **Demo** for the rehearsed narrative.

---

## Full AWS path (needs IAM permissions this key doesn't currently have)

Keep this for later — once EC2/ECS/App Runner + `iam:PassRole` are granted on
the AWS account, or if this is a different account with broader access.

```
 EventBridge                         AWS us-east-1
 ┌───────────┐  hourly   ┌────────────────────┐   ┌──────────────┐
 │ rate(1h)  ├──────────▶│ jobs: refresh      │──▶│  S3 bucket   │
 │ cron weekly├─────────▶│ jobs: retrain+gate │──▶│ hot/vayu.duckdb│
 └───────────┘           └────────────────────┘   └──────┬───────┘
                                                          │ pull on boot
 Bedrock (Nova) ◀─ scout ─▶ Tavily            ┌───────────▼──────────┐
                                              │ API: Fargate/App Runner│
                                              │ FastAPI + hot DuckDB   │
                                              └───────────┬──────────┘
                                        Vercel (Next.js) ◀┘
```

## 0. Prerequisites (already provided in `.env`)

| Var | Purpose |
|---|---|
| `AWS_REGION=us-east-1` | matches the IAM user + S3 bucket |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | app + jobs creds (or use a task role) |
| `VAYU_S3_BUCKET` / `VAYU_S3_PREFIX` | hot DB + history location |
| `BEDROCK_MODEL_ID=us.amazon.nova-pro-v1:0` | scout LLM (regional inference profile) |
| `SEARCH_PROVIDER=tavily` + `TAVILY_API_KEY` | scout web search |
| `DATA_GOV_IN_API_KEY`, `OPENAQ_API_KEY`, `FIRMS_API_KEY` | live ingest |
| `DEMO_MODE=false` | live wall clock + live feeds |

**IAM (minimum):** S3 `GetObject/PutObject/ListBucket/DeleteObject` on the bucket;
Bedrock `InvokeModel`. (The provided user has the broader managed policies, which
also cover this.)

## 1. Seed S3 once (from a machine with the repo)

```bash
make seed                     # builds models/artifacts + local data/vayu.duckdb
DEMO_MODE=false python -c "from vayu_core.storage import push_hot_db; push_hot_db()"
```

## 2. Build & push images (ECR)

```bash
aws ecr create-repository --repository-name vayu-api  --region us-east-1
aws ecr create-repository --repository-name vayu-jobs --region us-east-1
# docker build with the Dockerfiles in deploy/, tag, and `docker push` to ECR.
docker build -f deploy/Dockerfile.api  -t <acct>.dkr.ecr.us-east-1.amazonaws.com/vayu-api  .
docker build -f deploy/Dockerfile.jobs -t <acct>.dkr.ecr.us-east-1.amazonaws.com/vayu-jobs .
```

## 3. Run the API

- **App Runner** (simplest) or a **Fargate service**, port 8000, from `vayu-api`.
- Env: the table above. Health check: `GET /api/v1/health`.

## 4. Schedule the jobs (EventBridge → Fargate task)

- Task from `vayu-jobs`. Two EventBridge rules targeting the same task def:
  - `rate(1 hour)` → command `["python","-m","services.jobs.refresh"]`
  - `cron(0 20 ? * SUN *)` → command `["python","-m","services.jobs.retrain"]`
- `refresh` ingests latest CPCB/OpenAQ/Open-Meteo/FIRMS, scores the current hour
  (fast windowed path), optionally runs the scout (`--scout`), and pushes the hot
  DB. `retrain` retrains behind the **promotion gate** (only replaces the live
  model if it still beats persistence at t+24h) and pushes.

## 5. Web (Vercel)

```
NEXT_PUBLIC_API_URL = https://<api-host>          # no /api/v1 suffix — see next.config.js rewrites()
NEXT_PUBLIC_MAPPLS_KEY = <optional, official India boundary basemap>
```
`cd apps/web && vercel --prod` (or connect the repo). The Next.js rewrite proxies
`/api/v1/*` server-side, so the browser stays same-origin — no CORS setup needed.

## Cost

~$30–60/month: one small Fargate/App Runner service, hourly spot tasks, S3,
Vercel hobby, EventBridge (free), Bedrock scout a few $/mo at 4–6 runs/day.

## What stays true in production (stated, not hidden)

1. **Verification is T+48h** — it needs after-the-fact data.
2. **Retrain is gated** — a model that can't beat persistence is auto-rolled-back.
3. **"Live" = last reading** (CPCB/OpenAQ 30–120 min, FIRMS ~3h) — shown, not hidden.
4. **Scouted evidence is advisory** until a human promotes it.
