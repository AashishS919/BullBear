import { useCallback, useEffect, useState } from 'react'

/**
 * Run an async API function on mount (and when deps change), tracking
 * loading/error/data and exposing a reload().
 */
export function useApi(fn, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps)

  const load = useCallback(() => {
    let alive = true
    setLoading(true)
    setError(null)
    Promise.resolve(run())
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [run])

  useEffect(load, [load])

  return { data, error, loading, reload: load }
}
