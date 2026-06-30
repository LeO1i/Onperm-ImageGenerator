import { useCallback, useEffect, useRef, useState } from 'react'
import type { JobSSEEvent } from '../api/types'

interface UseJobSSEOptions {
  jobId: string | null
  enabled?: boolean
  onEvent?: (event: JobSSEEvent) => void
}

export function useJobSSE({ jobId, enabled = true, onEvent }: UseJobSSEOptions) {
  const [connected, setConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState<JobSSEEvent | null>(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  const connect = useCallback(() => {
    if (!jobId || !enabled) return () => {}

    const source = new EventSource(
      `/api/jobs/${encodeURIComponent(jobId)}/events`,
    )

    source.onopen = () => setConnected(true)
    source.onerror = () => setConnected(false)

    const handleMessage = (raw: MessageEvent) => {
      try {
        const event = JSON.parse(raw.data) as JobSSEEvent
        setLastEvent(event)
        onEventRef.current?.(event)
      } catch {
        // ignore malformed events
      }
    }

    source.addEventListener('message', handleMessage)
    source.addEventListener('step', handleMessage)
    source.addEventListener('progress', handleMessage)
    source.addEventListener('image_completed', handleMessage)
    source.addEventListener('failed', handleMessage)
    source.addEventListener('done', handleMessage)

    return () => {
      source.close()
      setConnected(false)
    }
  }, [jobId, enabled])

  useEffect(() => {
    return connect()
  }, [connect])

  return { connected, lastEvent }
}
