import type { DocumentSummary, QueryResponse } from './types'

const API_PREFIX = import.meta.env.VITE_API_PREFIX ?? '/api/v1'

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const payload = await response.json() as { detail?: unknown }
      if (typeof payload.detail === 'string') {
        detail = payload.detail
      } else if (Array.isArray(payload.detail)) {
        const messages = payload.detail
          .map((item) => {
            if (typeof item === 'string') return item
            if (item && typeof item === 'object' && 'msg' in item) {
              return String((item as { msg: unknown }).msg)
            }
            return ''
          })
          .filter(Boolean)
        if (messages.length) detail = messages.join(' ')
      }
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
