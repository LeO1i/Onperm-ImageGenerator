import { apiFetch } from './client'
import type { PreflightResult } from './types'

export async function fetchPreflight(): Promise<PreflightResult> {
  return apiFetch<PreflightResult>('/api/system/preflight')
}

export async function fetchPreflightStatus(): Promise<PreflightResult> {
  return apiFetch<PreflightResult>('/api/system/preflight/status')
}

export async function rerunPreflight(): Promise<PreflightResult> {
  return apiFetch<PreflightResult>('/api/system/preflight/rerun', {
    method: 'POST',
  })
}

export async function fetchHealth(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/api/health')
}
