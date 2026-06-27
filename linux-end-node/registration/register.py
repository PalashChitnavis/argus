import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = os.getenv("ARGUS_SERVER_URL")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")


def is_registered():
    return os.path.exists(CREDENTIALS_FILE)


def load_credentials():
    if not is_registered():
        return None
    with open(CREDENTIALS_FILE, "r") as f:
        return json.load(f)


def _save_credentials(node_id, api_key):
    credentials = {"node_id": node_id, "api_key": api_key}
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(credentials, f)


def register_node(machine_id, hostname, enrollment_token=None):
    """
    Registers this node with the server.

    enrollment_token: passed in from agent.py (either read from .env
    or collected interactively). Falls back to ARGUS_ENROLLMENT_TOKEN
    env var for backward compatibility (e.g. automated deployments
    that still set it in .env directly).
    """
    token = enrollment_token or os.getenv("ARGUS_ENROLLMENT_TOKEN", "").strip()

    if not token or token == "replace-with-real-token-later":
        print("[registration] No valid enrollment token. Cannot register.", flush=True)
        return False

    url = f"{SERVER_URL}/register"
    payload = {
        "enrollment_token": token,
        "machine_id": machine_id,
        "hostname": hostname,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        data    = response.json()
        node_id = data["node_id"]
        api_key = data["api_key"]

        _save_credentials(node_id, api_key)
        print(f"[registration] Successfully registered as node_id={node_id}", flush=True)
        return True

    except requests.exceptions.Timeout:
        print("[registration] Registration timed out — server unreachable.", flush=True)
        return False

    except requests.exceptions.ConnectionError:
        print("[registration] Could not connect to server.", flush=True)
        return False

    except requests.exceptions.HTTPError:
        print(f"[registration] Server rejected registration: {response.status_code} — {response.text}", flush=True)
        return False