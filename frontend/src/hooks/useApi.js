import { useCallback, useEffect, useState } from "react";

/**
 * Load data from the backend and keep track of loading and errors.
 *
 *   const { data, loading, error, reload } = useApi(() => api.get("/api/courses"));
 *
 * deps: values that, when they change, mean "load again" (e.g. a course id from the URL).
 * reload(): load again on demand, e.g. after creating something or from a Retry button.
 */
export default function useApi(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: "" });
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    // If the page changes before the answer arrives, ignore the old answer.
    let ignore = false;
    setState((previous) => ({ ...previous, loading: true, error: "" }));

    fetcher()
      .then((data) => {
        if (!ignore) setState({ data, loading: false, error: "" });
      })
      .catch((err) => {
        if (!ignore) setState({ data: null, loading: false, error: err.message });
      });

    return () => {
      ignore = true;
    };
    // fetcher is a new function on every render, so the caller lists what it depends on instead.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadCount]);

  const reload = useCallback(() => setReloadCount((count) => count + 1), []);

  return { ...state, reload };
}
