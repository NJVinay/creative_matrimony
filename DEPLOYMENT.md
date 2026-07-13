# Deployment Guide

## What the app needs from a host

Before comparing platforms, these are the hard requirements the backend
imposes — they decide everything:

1. **A long-running server process.** Chat runs over WebSockets
   (`/api/chat/rooms/{id}/ws`) with an in-memory connection manager.
   Serverless functions (Vercel/Netlify) spin up per-request and cannot hold
   WebSocket connections or shared in-memory state.
2. **Python runtime** (FastAPI + uvicorn).
3. **Outbound HTTPS** to Neon (Postgres) and Resend (email) — every host has this.
4. **Disk for uploads** (photos, horoscope charts). Nice-to-have; every free
   tier gives only *ephemeral* disk, so files vanish on redeploy regardless
   of platform. S3/Cloudflare R2 is the eventual fix.

The frontend is a standard Next.js 16 app (`next start`) — it runs anywhere
Node runs, and best of all on Vercel.

## Platform comparison (free tiers, July 2026)

| Platform | FastAPI backend? | Next.js frontend? | WebSockets? | Both in one place? | Notes |
|---|---|---|---|---|---|
| **Render** | ✅ native Python web service | ✅ Node web service | ✅ | ✅ **yes — the only mainstream free host that runs both** | Services sleep after ~15 min idle (~50 s cold start); 750 free instance-hours/month shared across services |
| **Vercel** | ⚠️ Python = serverless functions only | ✅ best-in-class | ❌ on functions | ❌ | Perfect for the frontend; cannot run the chat backend |
| **Netlify** | ❌ no Python runtime at all (static + JS/Go functions) | ✅ | ❌ | ❌ | **Cannot host this backend — repurpose or drop it** |
| **Koyeb** | ✅ | ✅ | ✅ | ❌ free tier allows only **one** service | Good backend-only alternative to Render |
| **Railway** | ✅ | ✅ | ✅ | ⚠️ | No permanent free tier anymore (one-time $5 trial credit) |
| **Fly.io** | ✅ (Docker) | ✅ (Docker) | ✅ | ⚠️ | Now pay-as-you-go; needs card + Docker ops; not really "free tier" |
| **Oracle Cloud Always-Free VPS** | ✅ | ✅ | ✅ | ✅ via docker-compose | Genuinely free forever (4 ARM cores/24 GB) but you own nginx, SSL, updates, backups — real ops burden |

### Recommendation

- **Single platform (what you asked for): Render.** It is the only mainstream
  free tier that hosts both services, and this repo already contains a
  [render.yaml](render.yaml) blueprint that creates both from one click.
- **Slightly better UX split: Vercel (frontend) + Render (backend).** You
  already have Vercel; it never cold-starts for pages, has the best Next.js
  build pipeline, and free-tier CDN. Only the API then has Render's ~50 s
  wake-up. This is what I'd actually run.
- Either way: **Neon stays the DB, Resend the email. Netlify has no role** —
  it cannot execute Python.

## Option A — everything on Render (single platform, one repo)

1. Push the repo to GitHub.
2. Create a Neon project → copy the connection string
   (`postgresql://...sslmode=require`). Paste it as-is — the app converts it
   to the asyncpg dialect automatically ([database.py](backend/app/database.py)).
3. Render Dashboard → **New → Blueprint** → select the repo. Render reads
   [render.yaml](render.yaml) and creates:
   - `matrimony-backend` — Python service, `rootDir: backend`, starts with
     `alembic upgrade head && uvicorn ...` (Neon schema migrates on every deploy)
   - `matrimony-frontend` — Node service, `rootDir: frontend`
4. Fill the secrets it prompts for: `DATABASE_URL`, `RESEND_API_KEY`.
5. After first deploy, set the real URLs and redeploy:
   - backend `CORS_ORIGINS=["https://matrimony-frontend.onrender.com"]`
   - frontend `NEXT_PUBLIC_API_URL=https://matrimony-backend.onrender.com`

## Option B — same GitHub repo, split across Vercel + Render

This is the "add frontend and backend paths separately" flow you described,
and it works cleanly because both platforms support monorepo subdirectories:

**Frontend on Vercel**
1. Vercel → Add New Project → import the GitHub repo.
2. **Root Directory** = `frontend` (Framework preset auto-detects Next.js).
3. Env var: `NEXT_PUBLIC_API_URL=https://<backend>.onrender.com`.
4. Optional but recommended — skip builds when only the backend changed:
   Project Settings → Git → **Ignored Build Step**:
   `git diff --quiet HEAD^ HEAD -- .` (runs inside `frontend/`, so it exits
   non-zero → build only when frontend files changed).

**Backend on Render**
1. Render → New → Web Service → same GitHub repo.
2. **Root Directory** = `backend`, Runtime = Python.
3. Build: `pip install -r requirements.txt`
   Start: `alembic upgrade head && uvicorn app.main:application --host 0.0.0.0 --port $PORT`
4. Env vars: `DATABASE_URL` (Neon), `JWT_SECRET`, `RESEND_API_KEY`,
   `CORS_ORIGINS=["https://<your-app>.vercel.app"]`, `COOKIE_SAMESITE=none`,
   `DEBUG=false`, `PYTHON_VERSION=3.12.7`.
5. Optional — Settings → Build & Deploy → **Build Filters** → Included paths:
   `backend/**` (skips deploys for frontend-only commits).

Both platforms redeploy automatically on push to `master`; each only rebuilds
its own half if you set the path filters above.

## Cross-domain cookie caveat (read before going live)

Auth uses httpOnly cookies. With the frontend on `*.vercel.app` and API on
`*.onrender.com` (or even two `onrender.com` subdomains — that domain is on
the Public Suffix List), the browser treats the auth cookie as third-party:

- `COOKIE_SAMESITE=none` (already the default in render.yaml) makes login
  work in **Chrome, Edge, Firefox**.
- **Safari blocks third-party cookies entirely.** The chat WebSocket has a
  `?token=` fallback, but REST calls from Safari will not carry the cookie.
- **Permanent fix (₹700–900/yr):** buy one domain and point subdomains at
  each service — `www.yourapp.in` → frontend, `api.yourapp.in` → backend.
  Custom domains are free on Render, Vercel, and Netlify. Same-site cookies
  then work everywhere; set `COOKIE_SAMESITE=lax` back.

## Scheduled jobs (weekly digest + session reminders)

Two admin-only endpoints are built to be cron targets:

- `POST /api/admin/digest/send` — weekly match digest (consented users only)
- `POST /api/expert/admin/sessions/send-reminders` — reminders for sessions in the next 24 h

Render's native cron jobs are paid, so on the free tier use a **GitHub
Actions scheduled workflow** (free in your existing repo):

```yaml
# .github/workflows/weekly-digest.yml
name: Weekly digest
on:
  schedule:
    - cron: "30 3 * * 6"   # Saturdays 09:00 IST
jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - run: |
          curl -sf -X POST "$API/api/auth/otp/request" ... # or use a long-lived admin token
        env:
          API: https://matrimony-backend.onrender.com
```

(Practical tip: mint an admin access token with a long
`ACCESS_TOKEN_EXPIRE_MINUTES` once and store it as a GitHub secret, or add a
shared-secret header check to those two endpoints later.)

The same trick with a 10-minute schedule doubles as a keep-warm ping so the
free Render service rarely cold-starts.

## Free-tier limits to keep in mind

- **Cold starts:** Render free services sleep after ~15 min idle; first
  request takes ~50 s. Keep-warm pings mitigate it.
- **Ephemeral uploads:** photos/horoscope charts are lost on every backend
  redeploy. Before real users upload photos, implement the `s3` storage
  backend (Cloudflare R2's free tier: 10 GB) — the `STORAGE_BACKEND` config
  hook already exists.
- **Single instance:** the in-memory chat WebSocket manager and rate limiter
  assume one process. Fine on a free instance; move to Redis pub/sub before
  scaling out (already marked with a TODO in [chat.py](backend/app/api/chat.py)).
- **Neon free tier:** 0.5 GB storage, autosuspends after 5 min idle
  (~1 s resume — negligible next to Render's cold start).
- **Resend free tier:** 100 emails/day, 3,000/month; sending domain must be
  verified in Resend before `EMAIL_FROM` can use it (until then the
  `onboarding@resend.dev` default works for testing to your own address).
