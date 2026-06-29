import { useCallback, useEffect, useState } from 'react';

// Fetches `fetcher()` whenever `deps` change, tracking loading/error state.
// Returns { data, loading, error, reload } — reload() re-runs the same fetcher
// without resetting `data` to null first (avoids UI flicker on manual refresh).
export function useFetch(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, reload: () => load(true), reset: () => load(false) };
}
