# Running Argus locally

Three pieces, three terminals: **backend** (FastAPI + Postgres), **frontend**
(React admin dashboard), **agent** (runs on whatever Linux machine you want
monitored — can be the same machine as the backend for testing).

Order matters: backend first, then generate an enrollment token, then the
agent, then the frontend (or frontend anytime after the backend is up).

---

## 1. Backend

**Requirements:** Python 3, PostgreSQL running locally with a database created for Argus.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:
```bash
DATABASE_URL=postgresql://<user>:<password>@localhost/argus
```

Create the tables (safe to re-run):
```bash
python init_db.py
```

**For anomaly detection testing/demo:** the scan needs at least 6 five-minute
telemetry windows (~30 min of real agent runtime) before it can find
anything. To test immediately instead of waiting, backfill synthetic
telemetry with an injected spike:
```bash
python seed_anomaly_demo_data.py <node_id>
```
(Needs a node to already exist — register one via the agent first, or check
`GET /nodes` for an id.)

Generate an enrollment token — the agent needs this to register:
```bash
python generate_token.py
```
This prints a token to the terminal. Copy it, you'll need it for step 3.

Start the server:
```bash
fastapi dev app/main.py
```
Backend is now at `http://127.0.0.1:8000`. Interactive API docs (Swagger UI)
at `http://127.0.0.1:8000/docs`.

---

## 2. Agent

Run this on the machine you want to monitor. It needs **root** — it reads
browser history DBs, firewall state, SSH config, etc., that aren't
world-readable.

```bash
cd agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `agent/.env`:
```bash
ARGUS_SERVER_URL=http://127.0.0.1:8000
ARGUS_ENROLLMENT_TOKEN=<token from generate_token.py>
```
(If you skip `ARGUS_ENROLLMENT_TOKEN`, the agent will prompt for it
interactively on first run instead.)

Start it:
```bash
sudo venv/bin/python3 agent.py
```
On first run it registers itself with the backend, saves credentials to
`agent/credentials.json`, then starts collecting on its schedule (CPU/processes
every 1 min, disk/RAM/network/connections every 5 min, browser history every
10 min, security/network-config every 30 min, OS/hardware/packages daily) and
polls for commands every 10 seconds in the background.

Registration only happens once — `credentials.json` existing is what the
agent checks. Delete that file to force re-registration (you'll need a fresh
enrollment token, since each one is single-use).

---

## 3. Frontend

```bash
cd frontend
npm install
```

Optional — only needed if your backend isn't at the default address:
create `frontend/.env`:
```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start it:
```bash
npm run dev
```
Vite will print the local URL (typically `http://localhost:5173`). Open it —
you should see the node you registered in step 2 once the agent's first
collection cycle lands.

---

## Quick sanity check

With all three running:
```bash
curl -s http://127.0.0.1:8000/nodes | python3 -m json.tool
```
Should list your registered node with `"status": "online"` (agent's
`last_seen` updates every 10s via its command-poll heartbeat, so it flips to
`offline` if the agent isn't running).

Anomaly detection sanity check (after seeding data or letting real telemetry
accumulate for ~30 min):
```bash
curl -s -X POST "http://127.0.0.1:8000/nodes/1/anomaly-scan?hours=6" | python3 -m json.tool
```
Should return `anomalies_found` and a list, or a `message` saying not enough
data yet.

For a full endpoint-by-endpoint reference with example curl calls, see
`API_REFERENCE.md` at the repo root.