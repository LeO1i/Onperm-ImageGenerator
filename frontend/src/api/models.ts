import { apiFetch } from './client'
import type { ModelsResponse, ModelItem } from './types'

export async function fetchModels(): Promise<ModelsResponse> {
  return apiFetch<ModelsResponse>('/api/models')
}

export async function refreshModels(): Promise<ModelsResponse> {
  return apiFetch<ModelsResponse>('/api/models/refresh', { method: 'POST' })
}

export async function downloadModel(modelId: string): Promise<ModelItem> {
  return apiFetch<ModelItem>(`/api/models/${encodeURIComponent(modelId)}/download`, {
    method: 'POST',
  })
}
