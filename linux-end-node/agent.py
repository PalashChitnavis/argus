import time
import sys

# We'll properly import and call our collector functions here once
# we build the scheduler. For now, this just proves the service
# itself starts, stays running, and logs correctly.

def main():
    print("Argus Linux end node agent starting up...", flush=True)

    while True:
        print("Agent heartbeat - still running.", flush=True)
        time.sleep(30)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Agent shutting down (received interrupt).", flush=True)
        sys.exit(0)