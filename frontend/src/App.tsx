import { FormEvent, useEffect, useRef, useState } from 'react'
import { askQuestion, fetchDocuments } from './api'
import { DocumentPanel } from './components/DocumentPanel'
import { SourceCard } from './components/SourceCard'
import type { DocumentSummary, Message } from './types'

const SAMPLE_QUESTIONS = [
  'What are the working hours at Partex?',
  'What happens if I am sick for more than seven days?',
  'How does annual leave under Partex policy compare with the Labour Act handbook?',
  'How many casual leave days are provided under the Labour Act handbook?',
]

const WELCOME_MESSAGE: Message = {
  id: 'welcome',
  role: 'assistant',
  text: 'Ask a question about Partex Star Group employee policy or the selected Bangladesh Labour Act handbook chapters. Answers include the source document name.',
}

function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const messageEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchDocuments()
      .then(setDocuments)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'Could not load the document list.')
      })
  }, [])

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function submitQuestion(value: string) {
    const cleaned = value.trim()
    if (!cleaned || loading) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      text: cleaned,
    }
    setMessages((current) => [...current, userMessage])
    setQuestion('')
    setError('')
    setLoading(true)

    try {
      const response = await askQuestion(cleaned)
      setMessages((current) => [
        ...current,
        {
          id: response.request_id,
          role: 'assistant',
          text: response.answer,
          answerable: response.answerable,
          sources: response.sources,
        },
      ])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The request could not be completed.')
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void submitQuestion(question)
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="brand-mark" aria-hidden="true">A</div>
        <div>
          <span className="eyebrow">AgamiSoft technical assessment</span>
          <h1>Enterprise AI Document Assistant</h1>
        </div>
        <div className="status-pill">
          <span className="status-dot" />
          Grounded document search
        </div>
      </header>

      <main className="workspace">
        <DocumentPanel documents={documents} />

        <section className="chat-panel">
          <div className="chat-panel__header">
            <div>
              <span className="eyebrow">Employee self-service</span>
              <h2>Policy assistant</h2>
            </div>
            <button
              type="button"
              className="text-button"
              onClick={() => setMessages([WELCOME_MESSAGE])}
            >
              Clear conversation
            </button>
          </div>

          <div className="chat-window" aria-live="polite">
            {messages.map((message) => (
              <article key={message.id} className={`message message--${message.role}`}>
                <div className="message__label">
                  {message.role === 'user' ? 'You' : 'Document assistant'}
                </div>
                <div className="message__bubble">
                  {message.text.split('\n').map((line, index) => (
                    <p key={`${message.id}-${index}`}>{line || '\u00a0'}</p>
                  ))}
                </div>
                {message.sources && message.sources.length > 0 && (
                  <div className="sources">
                    <h3>Sources</h3>
                    <div className="source-grid">
                      {Array.from(
                        new Map(message.sources.map((source) => [source.document_id, source])).values(),
                      ).map((source) => (
                        <SourceCard key={`${message.id}-${source.id}`} source={source} />
                      ))}
                    </div>
                  </div>
                )}
              </article>
            ))}

            {loading && (
              <article className="message message--assistant">
                <div className="message__label">Document assistant</div>
                <div className="message__bubble message__bubble--loading">
                  <span className="loading-bar" />
                  Searching the supplied documents
                </div>
              </article>
            )}
            <div ref={messageEndRef} />
          </div>

          <div className="question-area">
            {messages.length === 1 && (
              <div className="sample-questions">
                {SAMPLE_QUESTIONS.map((sample) => (
                  <button key={sample} type="button" onClick={() => void submitQuestion(sample)}>
                    {sample}
                  </button>
                ))}
              </div>
            )}

            {error && <div className="error-banner" role="alert">{error}</div>}

            <form className="question-form" onSubmit={handleSubmit}>
              <label htmlFor="question" className="sr-only">Ask a document question</label>
              <textarea
                id="question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask about leave, working hours, probation, conduct or employment conditions"
                rows={2}
                maxLength={1000}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    event.currentTarget.form?.requestSubmit()
                  }
                }}
              />
              <button type="submit" disabled={loading || question.trim().length < 3}>
                Ask question
              </button>
            </form>
            <p className="form-note">The assistant refuses questions that are not supported by the indexed documents.</p>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
