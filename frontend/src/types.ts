export type SourceReference = {
  id: string
  document_id: string
  document: string
  printed_page: number
  pdf_page: number
  section: string
  snippet: string
  source_category: 'company_policy' | 'law_handbook' | string
}

export type QueryResponse = {
  answerable: boolean
  answer: string
  sources: SourceReference[]
  request_id: string
}

export type DocumentSummary = {
  document_id: string
  title: string
  source_category: string
  page_count: number
  chunk_count: number
  scope: string
}

export type Message = {
  id: string
  role: 'user' | 'assistant'
  text: string
  sources?: SourceReference[]
  answerable?: boolean
}
