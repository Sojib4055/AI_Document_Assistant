import type { SourceReference } from '../types'

export function SourceCard({ source }: { source: SourceReference }) {
  return (
    <div className="source-name">
      <span className="source-name__icon" aria-hidden="true">✓</span>
      <span>{source.document}</span>
    </div>
  )
}
