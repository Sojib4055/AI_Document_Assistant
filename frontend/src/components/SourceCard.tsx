import type { SourceReference } from '../types'

export function SourceCard({ source }: { source: SourceReference }) {
  return (
    <div className="source-name">{source.document}</div>
  )
}
