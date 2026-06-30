export class ApiError extends Error {
  status: number
  detail?: string

  constructor(status: number, message: string, detail?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let detail: string | undefined
  try {
    const body = await response.json()
    detail = body.detail ?? body.message ?? JSON.stringify(body)
  } catch {
    detail = await response.text().catch(() => undefined)
  }
  return new ApiError(
    response.status,
    detail ?? `Request failed with status ${response.status}`,
    detail,
  )
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    ...init,
  })

  if (!response.ok) {
    throw await parseError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
