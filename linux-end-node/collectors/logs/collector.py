import subprocess
from datetime import datetime, timedelta
import sqlite3
import shutil
import tempfile
import glob
import os

def get_recent_logs(minutes_back=5):
    """
    Returns system log entries (from journald) generated in the last
    `minutes_back` minutes. Designed to be called on a recurring
    interval matching minutes_back, so each call picks up only new
    entries since the last one - similar in spirit to our process
    diffing logic, but for logs.
    """
    since_time = datetime.now() - timedelta(minutes=minutes_back)
    since_str = since_time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        result = subprocess.run(
            ["journalctl", "--since", since_str, "--no-pager", "-o", "short-iso"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    lines = result.stdout.strip().split("\n")
    # journalctl outputs a "-- Logs begin at ... --" header line we
    # don't want to treat as a real log entry, plus possible empty
    # output if there's nothing in this window
    log_lines = [line for line in lines if line and not line.startswith("-- ")]

    return log_lines

def get_auth_events(minutes_back=5):
    """
    Returns only authentication-related log entries (sudo, su, sshd)
    from the last `minutes_back` minutes. This is a focused subset of
    get_recent_logs() - same time-windowing approach, but filtered at
    the source to just the highest-signal security events instead of
    the full noisy log stream.
    """
    since_time = datetime.now() - timedelta(minutes=minutes_back)
    since_str = since_time.strftime("%Y-%m-%d %H:%M:%S")

    auth_programs = ["sudo", "su", "sshd"]
    events = []

    for program in auth_programs:
        try:
            result = subprocess.run(
                [
                    "journalctl",
                    "--since", since_str,
                    "--no-pager",
                    "-o", "short-iso",
                    "-t", program,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue  # this program may have produced no logs, or journalctl failed - skip and try the next

        lines = result.stdout.strip().split("\n")
        program_lines = [line for line in lines if line and not line.startswith("-- ")]
        events.extend(program_lines)

    return events

def _read_chromium_history(db_path, limit=50):
    """
    Reads history from a Chromium-based browser's SQLite History file
    (Chrome, Brave, Edge, Chromium all use identical schema).

    We copy the file to a temp location before reading because Chrome
    holds an exclusive lock on the file while running — reading it
    directly would either fail or return incomplete/corrupted data.
    """
    if not os.path.exists(db_path):
        return []

    # Copy to temp file to avoid the lock issue
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()

    try:
        shutil.copy2(db_path, tmp.name)

        conn = sqlite3.connect(tmp.name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # urls table columns we care about:
        # url          — full URL
        # title        — page title as shown in browser tab
        # visit_count  — total times this URL was visited (all time)
        # last_visit_time — microseconds since Jan 1, 1601 (Windows epoch)
        cursor.execute("""
            SELECT
                url,
                title,
                visit_count,
                last_visit_time
            FROM urls
            WHERE visit_count > 0
            ORDER BY visit_count DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            domain = _extract_domain(row["url"])
            if domain and _is_meaningful_domain(domain):
                results.append({
                    "url": row["url"],
                    "title": row["title"] or "",
                    "domain": domain,
                    "visit_count": row["visit_count"],
                    "last_visit_time": _convert_chrome_time(row["last_visit_time"]),
                })

        return results

    except sqlite3.Error:
        return []
    finally:
        os.unlink(tmp.name)


def _read_firefox_history(db_path, limit=50):
    """
    Reads history from Firefox's places.sqlite. Schema is different
    from Chromium — Firefox uses moz_places table with visit_count
    and last_visit_date (microseconds since Unix epoch, not
    Windows epoch like Chrome).
    """
    if not os.path.exists(db_path):
        return []

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()

    try:
        shutil.copy2(db_path, tmp.name)

        conn = sqlite3.connect(tmp.name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                url,
                title,
                visit_count,
                last_visit_date
            FROM moz_places
            WHERE visit_count > 0
                AND hidden = 0
            ORDER BY visit_count DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            domain = _extract_domain(row["url"])
            if domain and _is_meaningful_domain(domain):
                results.append({
                    "url": row["url"],
                    "title": row["title"] or "",
                    "domain": domain,
                    "visit_count": row["visit_count"],
                    "last_visit_time": _convert_firefox_time(row["last_visit_date"]),
                })

        return results

    except sqlite3.Error:
        return []
    finally:
        os.unlink(tmp.name)


def _extract_domain(url):
    """
    Extracts just the domain from a full URL.
    e.g. "https://www.youtube.com/watch?v=abc" → "youtube.com"
    Strips www. prefix for cleaner display.
    """
    try:
        # Simple split-based approach — avoids importing urllib
        # which adds overhead for something this straightforward
        if "://" in url:
            after_scheme = url.split("://", 1)[1]
        else:
            after_scheme = url

        domain = after_scheme.split("/")[0].split("?")[0].split("#")[0]

        # Remove port if present (e.g. localhost:3000)
        domain = domain.split(":")[0]

        # Strip www. prefix
        if domain.startswith("www."):
            domain = domain[4:]

        return domain.lower()
    except (IndexError, AttributeError):
        return None


def _convert_chrome_time(chrome_time):
    """
    Converts Chrome's timestamp format to a Unix timestamp.
    Chrome stores time as microseconds since Jan 1, 1601 (Windows
    FILETIME epoch) — very different from Unix's Jan 1, 1970 epoch.
    Difference between the two epochs is 11644473600 seconds.
    """
    if not chrome_time:
        return None
    try:
        return int(chrome_time / 1_000_000 - 11_644_473_600)
    except (TypeError, ValueError):
        return None


def _convert_firefox_time(firefox_time):
    """
    Converts Firefox's timestamp to a Unix timestamp.
    Firefox stores time as microseconds since Unix epoch (Jan 1,
    1970) — same epoch as Unix but in microseconds not seconds.
    """
    if not firefox_time:
        return None
    try:
        return int(firefox_time / 1_000_000)
    except (TypeError, ValueError):
        return None


def get_browser_history(limit=50):
    """
    Collects browsing history from all supported browsers found on
    this machine. Combines results across browsers and aggregates
    by domain, summing visit counts so you get a unified "most
    visited domains" view regardless of which browser was used.

    Supported: Chrome, Brave, Edge, Chromium (all Chromium-based),
    and Firefox.

    limit controls max entries pulled from each individual browser
    DB — the combined result is then re-sorted and capped at the
    same limit.
    """
    from collections import defaultdict

    # Resolve the actual home directory of the user who owns
    # the process — since we run as root, os.path.expanduser("~")
    # would give /root, not the real user's home. We find the
    # real home by looking at who owns the browser DB files.
    home_dirs = _find_home_directories()

    all_entries = []

    for home in home_dirs:
        # --- Chromium-based browsers ---
        chromium_paths = {
            "chrome":   os.path.join(home, ".config/google-chrome/Default/History"),
            "brave":    os.path.join(home, ".config/BraveSoftware/Brave-Browser/Default/History"),
            "edge":     os.path.join(home, ".config/microsoft-edge/Default/History"),
            "chromium": os.path.join(home, ".config/chromium/Default/History"),
        }

        for browser_name, db_path in chromium_paths.items():
            entries = _read_chromium_history(db_path, limit)
            for entry in entries:
                entry["browser"] = browser_name
            all_entries.extend(entries)

        # --- Firefox ---
        # Firefox uses a random profile directory name, so we glob
        # for any *.default-release or *.default profile folder
        firefox_patterns = [
            os.path.join(home, ".mozilla/firefox/*.default-release/places.sqlite"),
            os.path.join(home, ".mozilla/firefox/*.default/places.sqlite"),
        ]

        for pattern in firefox_patterns:
            for db_path in glob.glob(pattern):
                entries = _read_firefox_history(db_path, limit)
                for entry in entries:
                    entry["browser"] = "firefox"
                all_entries.extend(entries)

    if not all_entries:
        return []

    # Aggregate by domain across all browsers — sum visit counts,
    # keep the most recent last_visit_time, collect browser names
    domain_data = defaultdict(lambda: {
        "domain": "",
        "visit_count": 0,
        "last_visit_time": None,
        "browsers": set(),
        "sample_title": "",
    })

    for entry in all_entries:
        domain = entry["domain"]
        domain_data[domain]["domain"] = domain
        domain_data[domain]["visit_count"] += entry["visit_count"]
        domain_data[domain]["browsers"].add(entry["browser"])

        if not domain_data[domain]["sample_title"] and entry["title"]:
            domain_data[domain]["sample_title"] = entry["title"]

        # Keep the most recent visit time
        existing_time = domain_data[domain]["last_visit_time"]
        new_time = entry["last_visit_time"]
        if new_time and (existing_time is None or new_time > existing_time):
            domain_data[domain]["last_visit_time"] = new_time

    # Convert sets to lists for JSON serialisation
    result = []
    for domain, data in domain_data.items():
        result.append({
            "domain": data["domain"],
            "visit_count": data["visit_count"],
            "last_visit_time": data["last_visit_time"],
            "browsers": list(data["browsers"]),
        })

    result.sort(key=lambda x: x["visit_count"], reverse=True)
    return result[:limit]


def _find_home_directories():
    """
    Returns a list of real user home directories on this machine,
    excluding system accounts. Since we run as root, we can't rely
    on os.path.expanduser("~") — that gives /root. Instead we read
    /etc/passwd and return home dirs for users with UID >= 1000
    (the standard threshold for real human users on Linux).
    """
    home_dirs = []

    try:
        with open("/etc/passwd", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) < 7:
                    continue
                uid = int(parts[2])
                home = parts[5]
                # UID >= 1000 = real user account (not system account)
                if uid >= 1000 and os.path.isdir(home):
                    home_dirs.append(home)
    except (FileNotFoundError, ValueError):
        pass

    return home_dirs

def _is_meaningful_domain(domain):
    """
    Filters out internal, local, and noise domains that aren't
    meaningful for "most visited" reporting.
    """
    # Skip localhost variants
    if domain in ("localhost", "local", "localdomain"):
        return False

    # Skip mDNS (.local) and reverse DNS lookups
    if domain.endswith(".local") or domain.endswith(".arpa"):
        return False

    # Skip single-label names (not real internet domains)
    if "." not in domain:
        return False

    # Skip empty
    if not domain:
        return False

    return True

def get_recently_visited_sites(limit=50):
    """
    Returns the most recently visited sites across all supported
    browsers, sorted by visit time descending (most recent first).
    Each entry includes the full URL, page title, domain, when it
    was visited (Unix timestamp), and which browser recorded it.

    Does NOT include incognito/private browsing — browsers
    deliberately never write private sessions to the History
    database. This is by design at the browser level, not a
    limitation of this collector.
    """
    home_dirs = _find_home_directories()
    all_entries = []

    for home in home_dirs:
        # --- Chromium-based browsers ---
        chromium_paths = {
            "chrome":   os.path.join(home, ".config/google-chrome/Default/History"),
            "brave":    os.path.join(home, ".config/BraveSoftware/Brave-Browser/Default/History"),
            "edge":     os.path.join(home, ".config/microsoft-edge/Default/History"),
            "chromium": os.path.join(home, ".config/chromium/Default/History"),
        }

        for browser_name, db_path in chromium_paths.items():
            entries = _read_chromium_recent(db_path, limit)
            for entry in entries:
                entry["browser"] = browser_name
            all_entries.extend(entries)

        # --- Firefox ---
        firefox_patterns = [
            os.path.join(home, ".mozilla/firefox/*.default-release/places.sqlite"),
            os.path.join(home, ".mozilla/firefox/*.default/places.sqlite"),
        ]
        for pattern in firefox_patterns:
            for db_path in glob.glob(pattern):
                entries = _read_firefox_recent(db_path, limit)
                for entry in entries:
                    entry["browser"] = "firefox"
                all_entries.extend(entries)

    if not all_entries:
        return []

    # Sort all entries across all browsers by visit time, most recent first
    all_entries.sort(
        key=lambda x: x["last_visit_time"] or 0,
        reverse=True
    )

    return all_entries[:limit]


def _read_chromium_recent(db_path, limit=50):
    """
    Reads recent visits from a Chromium-based browser's History DB,
    joining the urls and visits tables to get one row per actual
    visit event (not just per URL) — so if you visited github.com
    10 times today, you get 10 entries with distinct timestamps,
    not one entry.

    visits.visit_time is Chrome's timestamp format (microseconds
    since Jan 1, 1601) — we convert to Unix timestamp.
    """
    if not os.path.exists(db_path):
        return []

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()

    try:
        shutil.copy2(db_path, tmp.name)
        conn = sqlite3.connect(tmp.name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Join urls + visits to get individual visit events with
        # timestamps. visits table has one row per actual page load,
        # urls table has the URL string and title.
        cursor.execute("""
            SELECT
                u.url,
                u.title,
                v.visit_time
            FROM visits v
            JOIN urls u ON v.url = u.id
            ORDER BY v.visit_time DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            domain = _extract_domain(row["url"])
            if not domain or not _is_meaningful_domain(domain):
                continue

            visit_time = _convert_chrome_time(row["visit_time"])

            results.append({
                "url": row["url"],
                "title": row["title"] or "",
                "domain": domain,
                "last_visit_time": visit_time,
            })

        return results

    except sqlite3.Error:
        return []
    finally:
        os.unlink(tmp.name)


def _read_firefox_recent(db_path, limit=50):
    """
    Reads recent visits from Firefox's places.sqlite, joining
    moz_places (URL/title) with moz_historyvisits (individual
    visit timestamps).

    visit_date is microseconds since Unix epoch.
    """
    if not os.path.exists(db_path):
        return []

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()

    try:
        shutil.copy2(db_path, tmp.name)
        conn = sqlite3.connect(tmp.name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                p.url,
                p.title,
                h.visit_date
            FROM moz_historyvisits h
            JOIN moz_places p ON h.place_id = p.id
            WHERE p.hidden = 0
            ORDER BY h.visit_date DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            domain = _extract_domain(row["url"])
            if not domain or not _is_meaningful_domain(domain):
                continue

            visit_time = _convert_firefox_time(row["visit_date"])

            results.append({
                "url": row["url"],
                "title": row["title"] or "",
                "domain": domain,
                "last_visit_time": visit_time,
            })

        return results

    except sqlite3.Error:
        return []
    finally:
        os.unlink(tmp.name)


if __name__ == "__main__":
    logs = get_recent_logs(minutes_back=5)
    print(f"Total log lines in last 5 minutes: {len(logs)}")
    for line in logs[:5]:
        print(line)

    print("\nAuth Events (last 5 minutes):")
    auth_events = get_auth_events(minutes_back=5)
    print(f"Total auth events: {len(auth_events)}")
    for event in auth_events:
        print(event)

    print("\nMost visited domains (all time, by frequency):")
    history = get_browser_history(limit=10)
    for entry in history:
        print(entry)

    print("\nRecently visited sites (by time, most recent first):")
    recent = get_recently_visited_sites(limit=10)
    for entry in recent:
        # Convert Unix timestamp to readable format for the test
        import datetime
        if entry["last_visit_time"]:
            readable = datetime.datetime.fromtimestamp(
                entry["last_visit_time"]
            ).strftime("%Y-%m-%d %H:%M:%S")
        else:
            readable = "unknown"
        print(f"{readable} | {entry['domain']} | {entry['title'][:50]} | {entry['browser']}")