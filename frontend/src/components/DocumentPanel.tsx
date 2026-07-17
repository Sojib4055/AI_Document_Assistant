import type { DocumentSummary } from '../types'

export function DocumentPanel({ documents }: { documents: DocumentSummary[] }) {
  return (
    <aside className="document-panel">
      <div className="document-panel__intro">
        <span className="eyebrow">Knowledge base</span>
        <div className="document-panel__title">
          <h2>Document scope</h2>
          <span>{documents.length} sources</span>
        </div>
        <p>Answers are restricted to the supplied employee handbook and selected Labour Act handbook pages.</p>
      </div>
      <div className="document-list">
        {documents.map((document) => (
          <article key={document.document_id} className="document-card">
            <span className="document-card__type">
              {document.source_category === 'company_policy' ? 'Policy' : 'Law reference'}
            </span>
            <h3>{document.title}</h3>
            <p>{document.scope}</p>
            <div className="document-card__meta">
              <span>{document.page_count} pages</span>
              <span>{document.chunk_count} sections</span>
            </div>
          </article>
        ))}
      </div>
      <div className="document-panel__note">
        The Labour Act handbook is used as an assessment source and is not legal advice.
      </div>
    </aside>
  )
}
