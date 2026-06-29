# Argus Frontend

A React (Vite) dashboard for the Argus backend, built around 3 pages per
node: **Overview**, **Telemetry**, and **Firewall**.

## Quick start — run the whole thing

Two terminals — backend and frontend.

**Terminal 1 — backend:**

```bash
cd argus-backend          # or argus-backend-patched/ from this delivery
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt

# .env needs your real DATABASE_URL, e.g.:
# DATABASE_URL=postgresql://argus_user:1234@localhost:5432/argus

python3 init_db.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Confirm it's up: `curl http://127.0.0.1:8000/nodes` should return `[]` or a
list of nodes.

**Terminal 2 — frontend (this folder):**

```bash
npm install
npm run dev
```

Open the printed URL (usually `http://localhost:5173`). No login needed.

If your backend runs somewhere other than `127.0.0.1:8000`, edit
`VITE_API_BASE_URL` in `.env` first.

## Pages

| Page | Route | What it shows |
|---|---|---|
| Nodes | `/nodes` | every registered node, online/offline |
| Overview | `/nodes/:id/overview` | hero stats (CPU/RAM/disk/security), system identity, network snapshot, most-visited sites |
| Telemetry | `/nodes/:id/telemetry` | every data type the agent collects, formatted for reading, each with its own "Refresh now" button |
| Firewall | `/nodes/:id/firewall` | rules in plain English ("Block incoming traffic on port 80"), create/edit/delete, status panel explaining enabled vs applied |

### How "Refresh now" works

Clicking it queues a command for the node and waits (polling every 2s, up
to ~20s) for the node to respond — it does **not** instantly change the
displayed value, since the node has to actually run that collector and
report back. You'll see the button cycle through "Queuing…" → "Waiting on
node…" → either the fresh result or "Node didn't respond" if the agent is
offline. See `BACKEND_CHANGES.md` for why this doesn't update stored
history.

## Every file in this project

```
argus-frontend/
  .env                          — VITE_API_BASE_URL
  index.html
  package.json / package-lock.json
  vite.config.js
  README.md
  public/
    favicon.svg
    icons.svg
  src/
    main.jsx                    — React root, router + toast provider
    App.jsx                     — route definitions
    styles.css                  — entire app's CSS (dark console theme)
    api/
      client.js                 — every backend call, one function per endpoint
    hooks/
      useFetch.js                — fetch/loading/error hook used by every page
      useRefreshCommand.js        — queues a refresh command, polls for its result
    lib/
      firewallText.js             — turns rule_type/action/params into plain English
    components/
      Layout.jsx                  — sidebar (node picker + nav) + page outlet
      StatusPill.jsx               — online/offline badge
      Toast.jsx                    — toast notification provider + hook
      ConfirmDialog.jsx            — generic delete-confirmation modal
      FirewallRuleForm.jsx         — create/edit modal, dynamic fields per rule type
      RefreshButton.jsx            — "Refresh now" button used throughout Telemetry
    pages/
      NodesPage.jsx                — /nodes
      OverviewPage.jsx             — /nodes/:nodeId/overview
      TelemetryPage.jsx            — /nodes/:nodeId/telemetry
      FirewallPage.jsx             — /nodes/:nodeId/firewall
```

## Building for production

```bash
npm run build
```

Output goes to `dist/`. Set `VITE_API_BASE_URL` to your real backend URL
first if it's not `127.0.0.1:8000`.

## Backend changes required

See `BACKEND_CHANGES.md` (one level up) for the full list — short version:
your `FirewallRule` model was out of sync with its own schema (every
firewall endpoint would have crashed), and there was no read API at all for
nodes or any telemetry data, which is almost certainly why your 5-minute
data call hung. Both are fixed in `argus-backend-patched/`.
