import { useEffect } from 'react';
import { useRefreshCommand } from '../hooks/useRefreshCommand';

const LABELS = {
  idle: 'Refresh now',
  queued: 'Queuing…',
  waiting: 'Waiting on node…',
  done: 'Refreshed',
  failed: 'Failed — try again',
  timeout: 'Node didn\'t respond',
};

/**
 * A "pull fresh data from the node right now" button for a telemetry
 * section. Queues a refresh command and reports back when the node
 * responds (usually within ~10-20s, since the agent polls every 10s).
 *
 * onResult(data) fires once the node's response comes back successfully,
 * so the parent section can display it alongside the regular history.
 */
export default function RefreshButton({ nodeId, collector, onResult }) {
  const { trigger, status, result } = useRefreshCommand(nodeId, collector);

  useEffect(() => {
    if (status === 'done' && result && onResult) {
      onResult(result);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, result]);

  const busy = status === 'queued' || status === 'waiting';

  return (
    <button className="btn btn-sm" onClick={trigger} disabled={busy}>
      {busy && <span className="refresh-spin">⟳</span>}
      {LABELS[status]}
    </button>
  );
}
