# Argus Frontend

A small React (Vite) dashboard for the Argus backend. Covers every endpoint in
`API_DOCUMENTATION.md`: nodes, telemetry (read-only), firewall rules (full
CRUD), and commands (create + manage).

## Quick start — run the whole thing

You need two things running at once: the **backend** (FastAPI + Postgres)
and this **frontend** (Vite dev server). Two terminals.

**Terminal 1 — backend** (use your existing `argus-backend` folder, with the
CORS fix from `BACKEND_FIXES.md` applied — or use `argus-backend-patched/`
from this delivery, which already has it):

```bash
cd argus-backend
python3 -m venv venv
. venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# make sure .env has your real DATABASE_URL, e.g.:
# DATABASE_URL=postgresql://argus_user:1234@localhost:5432/argus

python3 init_db.py            # creates tables, if not already done
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Leave this running. Confirm it's up: `curl http://127.0.0.1:8000/nodes`
should return `[]` or a list of nodes — not an error.

**Terminal 2 — frontend** (this folder):

```bash
cd argus-frontend
npm install
npm run dev
```

Open the URL it prints (usually `http://localhost:5173`). That's it — no
login, no build step needed for local use.

If your backend runs somewhere other than `127.0.0.1:8000`, edit `.env` in
this folder (`VITE_API_BASE_URL=...`) before running `npm run dev`.

If the frontend loads but shows a connection/network error, it's almost
always one of: backend not running, wrong `VITE_API_BASE_URL`, or the CORS
middleware fix from `BACKEND_FIXES.md` not applied yet.

## Pages

| Page | Route | What it does |
|---|---|---|
| Nodes | `/nodes` | List all registered nodes, online/offline status |
| Dashboard | `/nodes/:id/dashboard` | Combined live view — CPU/RAM/disk, OS info, security posture, recent connections |
| Telemetry | `/nodes/:id/telemetry` | Tabbed history for 1-min / 5-min / 30-min / daily / startup data |
| Firewall Rules | `/nodes/:id/firewall` | Full CRUD — create/edit/delete rules for all 6 rule types, with status summary |
| Commands | `/nodes/:id/commands` | Queue refresh/enforce/delete-rule/get-rules commands, view history + results |

No login/auth screen — the frontend-admin endpoints in your backend are
unauthenticated by design (only the Linux-end-node endpoints require a
Bearer token, and those aren't used here).

## Every file in this project

```
argus-frontend/
  .env                          — VITE_API_BASE_URL (backend URL)
  .gitignore
  index.html                    — Vite entry HTML, sets page title
  package.json / package-lock.json
  vite.config.js
  README.md                     — this file
  public/
    favicon.svg
    icons.svg
  src/
    main.jsx                    — React root, router + toast provider setup
    App.jsx                     — route definitions
    styles.css                  — entire app's CSS (dark console theme)
    api/
      client.js                 — every backend call, one function per endpoint
    hooks/
      useFetch.js                — fetch/loading/error hook used by every page
    components/
      Layout.jsx                 — sidebar (node picker + nav) + page outlet
      StatusPill.jsx              — online/offline badge
      Toast.jsx                   — toast notification provider + hook
      ConfirmDialog.jsx           — generic delete-confirmation modal
      FirewallRuleForm.jsx        — create/edit modal, dynamic fields per rule type
      CommandForm.jsx             — new-command modal (refresh/enforce/delete-rule/get-rules)
    pages/
      NodesPage.jsx               — /nodes
      DashboardPage.jsx           — /nodes/:nodeId/dashboard
      TelemetryPage.jsx           — /nodes/:nodeId/telemetry
      FirewallPage.jsx            — /nodes/:nodeId/firewall
      CommandsPage.jsx            — /nodes/:nodeId/commands
```

That's the full list — nothing else is needed to run or build this project.

## Building for production

```bash
npm run build
```

Output goes to `dist/`, servable as static files from anywhere (nginx,
Vercel, etc). Set `VITE_API_BASE_URL` to your real backend URL before
building if it's not `127.0.0.1:8000`.

## Backend changes required

Your backend had **no CORS configuration**, which blocks a browser-based
frontend running on a different port from calling it at all. I added
`CORSMiddleware` to `app/main.py` — this is required for this frontend (or
any browser-based frontend) to work.

I also fixed two backend bugs found while testing this frontend against a
live instance — see `BACKEND_FIXES.md` in the project root for details.
Neither is required for the frontend to function against your real Postgres
setup, but the second one (the `/dashboard` endpoint) is worth applying since
it silently drops nested data on every deployment, not just in my test
environment.

## Project structure

```
src/
  api/client.js          — every backend call, one function per endpoint
  components/            — Layout, StatusPill, Toast, ConfirmDialog, form modals
  hooks/useFetch.js       — small fetch/loading/error hook used by every page
  pages/                  — one file per route
  styles.css              — single stylesheet, dark console theme
```

Everything is plain CSS (no Tailwind/UI library) and plain `fetch` (no
React Query) to keep the codebase small and easy to read end to end.

Your backend had **no CORS configuration**, which blocks a browser-based
frontend running on a different port from calling it at all. I added
`CORSMiddleware` to `app/main.py` — this is required for this frontend (or
any browser-based frontend) to work.

I also fixed two backend bugs found while testing this frontend against a
live instance — see `BACKEND_FIXES.md` in the project root for details.
Neither is required for the frontend to function against your real Postgres
setup, but the second one (the `/dashboard` endpoint) is worth applying since
it silently drops nested data on every deployment, not just in my test
environment.

## Project structure

```
src/
  api/client.js          — every backend call, one function per endpoint
  components/            — Layout, StatusPill, Toast, ConfirmDialog, form modals
  hooks/useFetch.js       — small fetch/loading/error hook used by every page
  pages/                  — one file per route
  styles.css              — single stylesheet, dark console theme
```

Everything is plain CSS (no Tailwind/UI library) and plain `fetch` (no
React Query) to keep the codebase small and easy to read end to end.
