import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = os.getenv("ARGUS_SERVER_URL")
API_KEY = os.getenv("ARGUS_API_KEY")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE_DIR = os.path.join(BASE_DIR, "queue")

def _get_api_key():
    """
    Returns the node's real API key from credentials.json,
    falling back to the .env placeholder if not registered yet.
    """
    try:
        with open("credentials.json", "r") as f:
            return json.load(f)["api_key"]
    except (FileNotFoundError, KeyError):
        return API_KEY

def _ensure_queue_dir():
    """Creates the local queue folder if it doesn't already exist."""
    os.makedirs(QUEUE_DIR, exist_ok=True)


def _queue_payload(endpoint, payload):
    """
    Saves a failed send to disk so it can be retried later instead of
    being lost. Each queued item is its own JSON file, named with a
    timestamp so files naturally sort in the order they were queued.
    """
    _ensure_queue_dir()

    timestamp = time.time()
    filename = f"{timestamp}_{endpoint}.json"
    filepath = os.path.join(QUEUE_DIR, filename)

    queued_item = {
        "endpoint": endpoint,
        "payload": payload,
    }

    with open(filepath, "w") as f:
        json.dump(queued_item, f)

    print(f"[transport] Queued failed send for retry: {filename}", flush=True)


def send_data(endpoint, payload):
    """
    Sends a JSON payload to the central server at the given endpoint.
    Returns True if the send succeeded, False otherwise. On failure,
    the payload is queued locally for retry rather than being lost.
    """
    url = f"{SERVER_URL}/{endpoint}"

    headers = {
    "Authorization": f"Bearer {_get_api_key()}",
    "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return True

    except requests.exceptions.Timeout:
        print(f"[transport] Timed out sending to {endpoint}", flush=True)
        _queue_payload(endpoint, payload)
        return False

    except requests.exceptions.ConnectionError:
        print(f"[transport] Could not connect to server for {endpoint}", flush=True)
        _queue_payload(endpoint, payload)
        return False

    except requests.exceptions.HTTPError:
        print(f"[transport] Server rejected {endpoint}: {response.status_code}", flush=True)
        # Deliberately NOT queuing here - explained below
        return False


def retry_queued_sends():
    """
    Attempts to resend everything currently in the local queue.
    Successfully sent items are deleted from disk; failures stay
    queued for the next retry attempt.
    """
    _ensure_queue_dir()

    queued_files = sorted(os.listdir(QUEUE_DIR))

    if not queued_files:
        return

    print(f"[transport] Retrying {len(queued_files)} queued item(s)...", flush=True)

    for filename in queued_files:
        filepath = os.path.join(QUEUE_DIR, filename)

        with open(filepath, "r") as f:
            queued_item = json.load(f)

        endpoint = queued_item["endpoint"]
        payload = queued_item["payload"]

        url = f"{SERVER_URL}/{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {_get_api_key()}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()

            os.remove(filepath)
            print(f"[transport] Successfully resent and cleared: {filename}", flush=True)

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError):
            # Still failing - leave it queued, try again next time
            print(f"[transport] Still failing, left in queue: {filename}", flush=True)
            continue