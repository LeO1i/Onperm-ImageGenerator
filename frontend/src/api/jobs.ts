import { apiFetch } from './client'
import type {
  AppSettings,
  CreateJobInput,
  Job,
  JobsListResponse,
  RecentImage,
} from './types'

export async function fetchSettings(): Promise<AppSettings> {
  return apiFetch<AppSettings>('/api/settings')
}

export async function updateSettings(
  settings: Partial<AppSettings>,
): Promise<AppSettings> {
  return apiFetch<AppSettings>('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  })
}

export async function validateOutputDirectory(
  path: string,
): Promise<{ valid: boolean; message?: string }> {
  return apiFetch('/api/settings/output-directory/validate', {
    method: 'POST',
    body: JSON.stringify({ path }),
  })
}

export async function browseOutputDirectory(): Promise<{ path: string | null }> {
  return apiFetch('/api/settings/output-directory/browse', { method: 'POST' })
}

export async function fetchJobs(params?: {
  status?: string
  limit?: number
  offset?: number
}): Promise<JobsListResponse> {
  const search = new URLSearchParams()
  if (params?.status) search.set('status', params.status)
  if (params?.limit != null) search.set('limit', String(params.limit))
  if (params?.offset != null) search.set('offset', String(params.offset))
  const query = search.toString()
  return apiFetch<JobsListResponse>(`/api/jobs${query ? `?${query}` : ''}`)
}

export async function fetchJob(jobId: string): Promise<Job> {
  return apiFetch<Job>(`/api/jobs/${encodeURIComponent(jobId)}`)
}

export async function createJob(input: CreateJobInput): Promise<Job> {
  return apiFetch<Job>('/api/jobs', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function cancelJob(jobId: string): Promise<Job> {
  return apiFetch<Job>(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: 'POST',
  })
}

export async function deleteJob(
  jobId: string,
  deleteFiles = false,
): Promise<void> {
  const query = deleteFiles ? '?delete_files=true' : ''
  return apiFetch(`/api/jobs/${encodeURIComponent(jobId)}${query}`, {
    method: 'DELETE',
  })
}

export async function fetchRecentImages(limit = 50): Promise<RecentImage[]> {
  const response = await apiFetch<{ images: RecentImage[] }>(
    `/api/jobs/recent-images?limit=${limit}`,
  )
  return response.images ?? []
}
