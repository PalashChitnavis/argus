# Argus Linux End Node — TODO / Future Work

## Known limitation: polling vs. event-driven monitoring

Our current design polls system state on fixed intervals (1 min / 5 min /
30 min / daily). This means any activity that fully starts AND ends
between two polls is invisible to us — no matter how short the interval,
this blind spot can never be fully closed by polling alone. The real fix
is event-driven monitoring, which reacts to kernel-level events the
instant they happen, instead of checking state periodically.

Identified gaps under the current design:
- A process that starts and exits within a ~60s window is invisible to
  the process diff logic.
- A file can be downloaded, executed, and deleted entirely between disk
  usage polls (5 min) — zero dedicated file-activity collector exists
  today.
- A network connection that opens and fully closes within a 5-min window
  won't appear in get_active_connections().
- A security setting (firewall, SSH config, AppArmor) can be toggled off
  and back on within a 30-min window without being caught.
- A package installed and removed within the same day is invisible
  (also: no diff logic exists yet for installed packages — only current
  state).
- USB device insert/copy/remove cycles are currently not monitored at
  all (no collector exists for this yet).
- While the laptop is suspended/asleep, the agent itself is paused —
  nothing is observed during that window.

---

## Future Work

### 1. Event-driven monitoring (highest priority future work)
- [ ] File activity collector using inotify — real-time create/modify/
      delete events for watched directories (e.g., Downloads, /tmp, home
      dir), instead of relying on aggregate disk usage polling.
- [ ] Process exec monitoring via auditd — real-time process start
      events as they happen, closing the short-lived-process blind spot.
- [ ] USB device monitoring via udev events — real-time insert/remove
      detection, rather than no coverage at all.
- [ ] Investigate eBPF as a longer-term replacement for the above —
      lower overhead, can hook file/process/network events in one
      unified framework. Bigger lift, treat as its own research phase.

### 2. Diff logic gaps
- [ ] Add diff logic for get_installed_packages() (only process diffing
      exists today) — detect packages installed/removed between two
      snapshots, not just current state.
- [ ] Add diff logic for security posture checks (firewall, SSH config,
      AppArmor) — detect "was toggled off and back on" patterns, not
      just current state at poll time.

### 3. Suspend/resume handling
- [ ] Detect when the system resumes from suspend (e.g., via systemd
      sleep hooks) and trigger an immediate out-of-cycle collection pass,
      so there's at least a before/after snapshot around sleep periods.

### 4. Data not yet collected (from original brainstorm, not yet built)
- [ ] System call frequency / syscall distribution sampling.
- [ ] Connection periodicity analysis (beaconing detection) — needs
      multiple connection samples over time, server-side logic likely.
- [ ] Process environment variables (for processes where accessible).
- [ ] Long-window resource trend analysis (multi-day load average creep)
      — likely a server-side aggregation task, not a new collector.

### 5. Deployment / packaging (already planned, not forgotten)
- [ ] Bash install script (install.sh) once agent.py is feature-complete.
- [ ] Convert to a .deb package with a postinst hook for fully automatic
      install (no manual systemd steps for the end user).

### 6. Privilege model refinement
- [ ] Investigate replacing full root with specific Linux capabilities
      (e.g., CAP_NET_ADMIN, CAP_SYS_PTRACE) instead of blanket root, per
      principle of least privilege. Deferred during initial build for
      simplicity.