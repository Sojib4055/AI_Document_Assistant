---
title: Enterprise AI Document Assistant
emoji: 📚
colorFrom: red
colorTo: gray
sdk: docker
app_port: 8000
pinned: false
---

# Enterprise AI Document Assistant

A retrieval-augmented document assistant built for the AgamiSoft AI Solutions Engineer technical assessment. The application answers employee questions from the supplied documents, returns the supporting source and printed page, and refuses questions that are not supported by the indexed material.

The repository is structured as a small production-style service rather than a single notebook. Document ingestion, retrieval, answer generation, API contracts and the browser interface are separate components.

## Assessment scope

The assessment brief describes a generic multi-document scenario. The files supplied for this implementation are:

- The complete Partex Star Group Employee Handbook, printed pages 1-10
- *A Handbook on the Bangladesh Labour Act, 2006*
  - Chapter II, printed pages 25-32: Conditions of Service and Employment
  - Chapter IX, printed pages 56-60: Working Hours and Leave

Only these documents and page ranges are searchable.

## Main capabilities

- Text extraction from the Partex handbook
- OCR path for the scanned Labour Act handbook
- Correct handling of printed page numbers and physical PDF page numbers
- Section-aware and clause-aware chunks with metadata
- Chroma vector retrieval combined with an in-memory BM25 index
- Reciprocal rank fusion for hybrid retrieval
- Strict document grounding and unsupported-question refusal
- Backend-controlled citations
- Separate treatment of company policy and legal handbook provisions
- FastAPI endpoints with Pydantic request and response models
- React interface with source cards and links to the original PDF page
- Automated ingestion, retrieval, API and refusal tests
- Docker image that builds and serves the frontend and backend together

## Architecture

### Runtime flow

1. The browser sends a question to `POST /api/v1/query`.
2. The backend creates a dense query embedding and runs Chroma search.
3. The same question is searched through BM25.
4. Reciprocal rank fusion combines both rankings.
5. An answerability gate checks query coverage and evidence overlap.
6. The generator receives only the selected chunks, each labelled `S1`, `S2` and so on.
7. The backend validates the returned source labels and resolves them to document and page metadata.

### Ingestion flow

1. Map physical PDF pages to printed pages.
2. Extract embedded text where available.
3. Use cached OCR text or Tesseract when no usable text layer exists.
4. Split the text by handbook heading or legal section.
5. Save normalized chunks to `data/processed/chunks.jsonl`.
6. Build or refresh the Chroma index when the corpus or embedding provider changes.

## Important page mapping

The citation requirement is based on the page printed inside the source, not only the page shown by a PDF viewer.

### Partex handbook

| Physical PDF page | Printed pages |
|---|---|
| 2 | 1 and 2 |
| 3 | 3 and 4 |
| 4 | 5 and 6 |
| 5 | 7 and 8 |
| 6 | 9 and 10 |

The ingestion loader splits every landscape spread before extracting text. For example, Partex working hours are cited as printed page 5 even though they are on physical PDF page 4.

### Labour Act handbook

| Assigned printed pages | Physical PDF pages |
|---|---|
| 25-32 | 42-49 |
| 56-60 | 73-77 |

Both values are stored in metadata. The UI displays the printed page and uses the physical page when opening the PDF.

## Quick start with Docker

Docker is the simplest way to run the complete application because the image includes Tesseract.

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Application: `http://localhost:8000`
- OpenAPI documentation: `http://localhost:8000/docs`
- Liveness: `http://localhost:8000/health/live`
- Readiness: `http://localhost:8000/api/v1/health/ready`

The application works without an API key by using the deterministic hash embedder and extractive answer fallback. For submission-quality answers, configure OpenAI as described below.

## OpenAI configuration

Edit `.env`:

```env
OPENAI_API_KEY=your_key_here
EMBEDDING_PROVIDER=openai
LLM_PROVIDER=openai
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

`auto` is also supported for both provider settings. When a key exists, `auto` selects OpenAI. Without a key, it selects the local fallback.

The model names are configuration values so they can be changed without modifying application code.

## Local development

### System requirements

- Python 3.12 recommended
- Node.js 22 recommended
- Tesseract 5 only when regenerating OCR from the scanned PDF

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp .env.example .env
PYTHONPATH=backend python backend/scripts/ingest.py --rebuild
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
Copy-Item .env.example .env
$env:PYTHONPATH = "backend"
python backend\scripts\ingest.py --rebuild
uvicorn app.main:app --reload --port 8000
```

### Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api` and `/health` to port 8000.

## Corpus regeneration

A normalized corpus and OCR cache are included so the project starts quickly. To rebuild the chunks from the source PDFs:

```bash
PYTHONPATH=backend python backend/scripts/ingest.py --rebuild
```

To ignore the OCR cache and run Tesseract again:

```bash
PYTHONPATH=backend python backend/scripts/ingest.py --rebuild --force-ocr
```

The script writes:

- `data/processed/chunks.jsonl`
- `data/processed/manifest.json`
- `data/processed/ocr/page_*.txt`

The Chroma index is not committed. It is generated from `chunks.jsonl` on application startup and persisted under `data/chroma`.

## API contracts

### Ask a question

`POST /api/v1/query`

```json
{
  "question": "What happens if I am sick for more than seven days?"
}
```

Example response:

```json
{
  "answerable": true,
  "answer": "A fitness certificate is required for prolonged sick leave of more than seven days.",
  "sources": [
    {
      "id": "S1",
      "document_id": "partex-star-employee-handbook",
      "document": "Partex Star Group Employee Handbook",
      "printed_page": 6,
      "pdf_page": 4,
      "section": "B. Leave - 2. Sick Leave",
      "snippet": "...",
      "source_category": "company_policy"
    }
  ],
  "request_id": "..."
}
```

### List indexed documents

`GET /api/v1/documents`

### Open a source PDF

`GET /api/v1/documents/{document_id}/file`

### Health checks

- `GET /health/live`
- `GET /api/v1/health/ready`

## Grounding and citation rules

The generator is not allowed to create a page number or document name. Retrieved chunks are labelled `S1`, `S2` and so on. The model may return those labels, but the API resolves the labels against server-side metadata. Unknown labels are discarded. An answer without a valid source is converted to the standard refusal response.

The grounding prompt also requires separate labels when company policy and the Labour Act handbook both apply. This prevents a company benefit from being incorrectly presented as the statutory rule, or the reverse.

The refusal text is:

> I don't have sufficient information in the provided documents to answer this question.

## Testing

Run the automated suite:

```bash
PYTHONPATH=backend pytest backend/tests -q
```

The tests cover:

- Printed page and physical page mapping
- Important numeric entitlement extraction
- Retrieval of the expected clause
- Source metadata in the final response
- Out-of-scope refusal
- Request validation and API response shape

Run the small retrieval evaluation:

```bash
PYTHONPATH=backend python backend/scripts/evaluate.py
```

Detailed results are written to `evaluation/results.json`. The evaluation checks expected document, section and page retrieval within the top five results as well as refusal behaviour.

## Project structure

```text
.
├── backend
│   ├── app
│   │   ├── api
│   │   ├── ingestion
│   │   ├── models
│   │   ├── services
│   │   └── main.py
│   ├── scripts
│   └── tests
├── data
│   ├── source
│   ├── processed
│   └── chroma
├── docs
├── evaluation
├── frontend
├── Dockerfile
└── docker-compose.yml
```

## Deployment

The root Dockerfile uses a two-stage build:

1. Node builds the Vite frontend.
2. Python installs the backend and Tesseract, then serves the frontend through FastAPI.

This can be deployed as one web service on a container platform. Set the start command from the Dockerfile and provide the environment variables in the platform dashboard. Attach a persistent disk to `/app/data/chroma` when available. Without a persistent disk, the small index can be rebuilt at startup.

## Business value

The assistant is designed for employee self-service rather than open-ended conversation. It reduces repeated HR questions, gives employees a traceable source, and makes policy differences visible. Refusal behaviour is important because an unsupported but confident answer can create more HR work and can be risky when employment rules are involved.

## Assumptions and limitations

- The searchable corpus is limited to the supplied files and assigned legal pages.
- The Labour Act file is a handbook and English translation supplied for the assessment. The application does not claim that it contains every later amendment or replaces the authoritative legal text.
- OCR is deterministic but not perfect. Key numbers and section headings in the assigned pages should be reviewed when replacing the source PDF.
- Authentication and role-based access are outside this assessment scope.
- Conversation history is kept in the browser and is not persisted.
- The local hash embedding and extractive generator are operational fallbacks. OpenAI mode is recommended for the final demonstration.

## Technical discussion notes

A reviewer may ask about the following choices:

- Why printed page mapping is separate from physical PDF page mapping
- Why OCR is page-level rather than document-level
- Why BM25 is retained beside dense retrieval
- How rank fusion works
- How the refusal gate behaves
- Why citations are resolved after generation
- How policy and legal sources are kept separate
- How the index is rebuilt when documents or embedding models change
