import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = os.getenv("ARGUS_SERVER_URL")
ENROLLMENT_TOKEN = os.getenv("ARGUS_ENROLLMENT_TOKEN")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")


def is_registered():
    """
    Checks whether this node has already completed registration, by
    checking if a local credentials file exists. This is what lets
    the agent decide, on every startup, whether to run the
    registration flow or skip straight to normal operation.
    """
    return os.path.exists(CREDENTIALS_FILE)


def load_credentials():
    """
    Reads the locally stored node_id and api_key, issued by the
    server during registration. Returns None if no credentials exist
    yet - callers should check is_registered() first.
    """
    if not is_registered():
        return None

    with open(CREDENTIALS_FILE, "r") as f:
        return json.load(f)


def _save_credentials(node_id, api_key):
    """
    Persists the node_id and api_key returned by the server after a
    successful registration, so future agent runs don't need to
    re-register.
    """
    credentials = {
        "node_id": node_id,
        "api_key": api_key,
    }

    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(credentials, f)


def register_node(machine_id, hostname):
    """
    Registers this node with the central server using the enrollment
    token from .env, plus this machine's identity. On success, saves
    the permanent node_id and api_key returned by the server. Returns
    True if registration succeeded, False otherwise.
    """
    if not ENROLLMENT_TOKEN or ENROLLMENT_TOKEN == "replace-with-real-token-later":
        print("[registration] No valid enrollment token set in .env. Cannot register.", flush=True)
        return False

    url = f"{SERVER_URL}/register"

    payload = {
        "enrollment_token": ENROLLMENT_TOKEN,
        "machine_id": machine_id,
        "hostname": hostname,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        data = response.json()
        node_id = data["node_id"]
        api_key = data["api_key"]

        _save_credentials(node_id, api_key)
        print(f"[registration] Successfully registered as node_id={node_id}", flush=True)
        return True

    except requests.exceptions.Timeout:
        print("[registration] Registration timed out - server unreachable.", flush=True)
        return False

    except requests.exceptions.ConnectionError:
        print("[registration] Could not connect to server for registration.", flush=True)
        return False

    except requests.exceptions.HTTPError:
        print(f"[registration] Server rejected registration: {response.status_code} - {response.text}", flush=True)
        return False