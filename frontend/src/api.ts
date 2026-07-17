import type { DocumentSummary, QueryResponse } from './types'

const API_PREFIX = import.meta.env.VITE_API_PREFIX ?? '/api/v1'

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const payload = await response.json() as { detail?: string }
      detail = payload.detail ?? detail
    } catch {
      // Keep the status-based message when the body is not JSON.
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  const response = await fetch(`${API_PREFIX}/documents`)
  return readJson<DocumentSummary[]>(response)
}

export async function askQuestion(question: string): Promise<QueryResponse> {
  const response = await fetch(`${API_PREFIX}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return readJson<QueryResponse>(response)
}
