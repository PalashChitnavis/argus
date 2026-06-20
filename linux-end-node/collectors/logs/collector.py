import subprocess
from datetime import datetime, timedelta

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

if __name__ == "__main__":
    logs = get_recent_logs(minutes_back=5)
    print(f"Total log lines in last 5 minutes: {len(logs)}")
    for line in logs[:10]:
        print(line)

    auth_events = get_auth_events(minutes_back=5)
    print(f"Total auth log lines in last 5 minutes: {len(auth_events)}")
    for line in auth_events[:10]:
        print(line)