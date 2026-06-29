import { useCallback, useRef, useState } from 'react';
import { createRefreshCommand, getCommand } from '../api/client';

/**
 * Queues a "refresh" command for a given collector, then polls the command's
 * own status every 2s (up to ~20s total) until the node reports a result.
 *
 * IMPORTANT: a refresh command's result is NOT written back into the
 * regular telemetry tables (cpu_snapshots, ram_snapshots, etc.) — it only
 * lands in the command's own result. The node still independently posts to
 * those tables on its normal schedule (every 1/5/30 min depending on type).
 * So this hook surfaces the on-demand result separately, as "just fetched
 * from the node right now", rather than pretending it updates history.
 */
export function useRefreshCommand(nodeId, collector) {
  const [status, setStatus] = useState('idle'); // idle | queued | waiting | done | failed | timeout
  const [result, setResult] = useState(null);
  const pollRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const trigger = useCallback(async () => {
    stopPolling();
    setStatus('queued');
    setResult(null);
    try {
      const { command_id } = await createRefreshCommand(nodeId, collector);
      setStatus('waiting');

      let attempts = 0;
      pollRef.current = setInterval(async () => {
        attempts += 1;
        try {
          const cmd = await getCommand(nodeId, command_id);
          if (cmd.executed) {
            stopPolling();
            if (cmd.result?.success) {
              setResult(cmd.result.data);
              setStatus('done');
            } else {
              setStatus('failed');
            }
          } else if (attempts >= 10) {
            // ~20s with no response — node likely offline or slow
            stopPolling();
            setStatus('timeout');
          }
        } catch {
          stopPolling();
          setStatus('failed');
        }
      }, 2000);
    } catch {
      setStatus('failed');
    }
  }, [nodeId, collector, stopPolling]);

  return { trigger, status, result };
}
