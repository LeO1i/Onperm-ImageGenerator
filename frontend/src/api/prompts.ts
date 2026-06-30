import { apiFetch } from './client'
import type {
  CreateSavedPromptInput,
  PromptTemplate,
  SavedPrompt,
} from './types'

export async function fetchTemplates(): Promise<PromptTemplate[]> {
  const response = await apiFetch<{ templates: PromptTemplate[] }>(
    '/api/prompts/templates',
  )
  return response.templates ?? []
}

export async function fetchSavedPrompts(params?: {
  q?: string
  tag?: string
  favorite?: boolean
}): Promise<SavedPrompt[]> {
  const search = new URLSearchParams()
  if (params?.q) search.set('q', params.q)
  if (params?.tag) search.set('tag', params.tag)
  if (params?.favorite) search.set('favorite', 'true')
  const query = search.toString()
  const response = await apiFetch<{ prompts: SavedPrompt[] }>(
    `/api/prompts/saved${query ? `?${query}` : ''}`,
  )
  return response.prompts ?? []
}

export async function fetchSavedPrompt(id: string): Promise<SavedPrompt> {
  return apiFetch<SavedPrompt>(`/api/prompts/saved/${encodeURIComponent(id)}`)
}

export async function createSavedPrompt(
  input: CreateSavedPromptInput,
): Promise<SavedPrompt> {
  return apiFetch<SavedPrompt>('/api/prompts/saved', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function updateSavedPrompt(
  id: string,
  input: Partial<CreateSavedPromptInput>,
): Promise<SavedPrompt> {
  return apiFetch<SavedPrompt>(`/api/prompts/saved/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(input),
  })
}

export async function deleteSavedPrompt(id: string): Promise<void> {
  return apiFetch(`/api/prompts/saved/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
}
