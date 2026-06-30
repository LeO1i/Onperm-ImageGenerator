import { useCallback, useEffect, useState } from 'react'
import {
  fetchPreflightStatus,
  rerunPreflight,
} from '../api/system'
import type { PreflightResult } from '../api/types'

const STALE_MS = 5 * 60 * 1000

export function usePreflight() {
  const [preflight, setPreflight] = useState<PreflightResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (force = false) => {
    setLoading(true)
    setError(null)
    try {
      const result = force
        ? await rerunPreflight()
        : await fetchPreflightStatus()
      setPreflight(result)
      return result
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to load system status'
      setError(message)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const isStale = useCallback(() => {
    if (!preflight?.checked_at) return true
    const checkedAt = new Date(preflight.checked_at).getTime()
    return Date.now() - checkedAt > STALE_MS
  }, [preflight])

  const ensureFresh = useCallback(async () => {
    if (!preflight || isStale()) {
      return load(true)
    }
    return preflight
  }, [preflight, isStale, load])

  useEffect(() => {
    void load()
  }, [load])

  return {
    preflight,
    loading,
    error,
    load,
    rerun: () => load(true),
    ensureFresh,
    canGenerate: preflight?.critical_passed ?? false,
  }
}
