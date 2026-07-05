# Mac mini RAG Runtime

Mac mini is the server-side source of truth for the Arvectum tender research
runtime.

## Server Checkout

- Main working checkout for the live smoke run:
  `/Users/master/Documents/AI-Corporation-live`
- The primary repository checkout on Mac mini may be dirty. Use the clean
  runtime checkout above for repeatable smoke runs.

## Database Runtime

- Docker PostgreSQL for Arvectum runs on host port `55432`
- Homebrew PostgreSQL already occupies `5432`, so Arvectum must point to `55432`
- Required runtime env var:

```bash
AI_CORP_DATABASE_URL=postgresql+psycopg://arvectum:<PASSWORD>@127.0.0.1:55432/arvectum
```

Do not commit real passwords or `.env*` files.

## Llama.cpp Services

- Chat LLM endpoint: `http://127.0.0.1:8088/v1`
- Embedding endpoint: `http://127.0.0.1:8090/v1`

Embedding model used in the validated smoke run:

- repo: `Qwen/Qwen3-Embedding-4B-GGUF`
- file:
  `/Users/master/models/embeddings/Qwen3-Embedding-4B-GGUF/Qwen3-Embedding-4B-Q8_0.gguf`

Validated embedding server command:

```bash
/opt/homebrew/bin/llama-server \
  --model /Users/master/models/embeddings/Qwen3-Embedding-4B-GGUF/Qwen3-Embedding-4B-Q8_0.gguf \
  --alias Qwen3-Embedding-4B \
  --embedding \
  --pooling last \
  --ctx-size 8192 \
  --parallel 1 \
  --batch-size 2048 \
  --ubatch-size 2048 \
  --threads 8 \
  --threads-batch 8 \
  --no-cont-batching \
  --port 8090
```

Why `batch-size/ubatch-size=2048`:

- one real production chunk tokenized to `1044` tokens;
- the earlier `1024` physical batch caused live failures;
- `2048` cleared the smoke run and kept the embedding server stable.

## Successful API Smoke

All smoke checks passed with `registry_number=0323100010326000013` using
the canonical runtime configuration.

### Canonical Database

- **Docker Postgres**: `pgvector/pgvector:pg17` on `127.0.0.1:55432`
- **Backend and CLI** must use the same `AI_CORP_DATABASE_URL`:

```bash
AI_CORP_DATABASE_URL=postgresql+psycopg://arvectum:<PASSWORD>@127.0.0.1:55432/arvectum
```

- **Health endpoint** (`GET /api/tender-research/health`) returns masked URL,
  migration head, pgvector status, and table counts. Use it to verify DB/runtime
  alignment after restart.

### Embedding and LLM Servers

- Embedding server: `http://127.0.0.1:8090/v1`, model `Qwen3-Embedding-4B`
- Chat LLM server: `http://127.0.0.1:8088/v1`
- Mac mini LLM model id: `/Users/master/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf`

### CLI Result

```bash
python -m src.tender_research.rag.cli analyze-tender \
  --registry-number 0323100010326000013 \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --base-url http://127.0.0.1:8090/v1 \
  --use-llm \
  --llm-base-url http://127.0.0.1:8088/v1 \
  --llm-model /Users/master/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf \
  --limit 8 \
  --save-report
```

Output:

| Field | Value |
|-------|-------|
| status | completed |
| sections_count | 10 |
| sources_count | 30 |
| used_llm | true |
| llm_model | /Users/master/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf |
| retrieval_provider | llama_cpp |
| retrieval_model | Qwen3-Embedding-4B |
| report_path | data/rag/reports/analyze_tender_0323100010326000013.md |

### API POST Result

```bash
curl -X POST http://127.0.0.1:8001/api/tender-research/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "registry_number": "0323100010326000013",
    "provider": "llama_cpp",
    "model": "Qwen3-Embedding-4B",
    "base_url": "http://127.0.0.1:8090/v1",
    "use_llm": true,
    "llm_base_url": "http://127.0.0.1:8088/v1",
    "llm_model": "/Users/master/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf",
    "limit": 8,
    "save_report": true
  }'
```

- HTTP 200
- status: completed
- sections_count: 10
- sources_count: 30
- report_markdown: not empty

### Latest Report Endpoint

```
GET /api/tender-research/analyze/0323100010326000013/latest
```

- report_markdown: returned (27091 chars)
- registry_number: correct
- Path traversal: blocked

### Health Endpoint

```
GET /api/tender-research/health
```

- database_url_masked: `postgresql+psycopg://arvectum:***@127.0.0.1:55432/arvectum`
- No secrets leaked
- Table counts returned for all procurement tables

### Demo UI Smoke

**No code changes were required.** The tab was already fully wired.

| Check | Result |
|-------|--------|
| Demo URL | `http://127.0.0.1:8001/demo/tender-agent` |
| Tab "Анализ закупки" present | PASS (data-tab & section both present) |
| Form with registry_number input | PASS |
| Checkboxes (use_llm, save_report) | PASS |
| JS handler `handleAnalysisForm` defined | PASS |
| API endpoint in fetch JSON call | PASS (`/api/tender-research/analyze`) |
| API POST precheck (same params) | HTTP 200, status=completed, sections=10, sources=30, used_llm=true |
| Report link `GET /latest` | HTTP 200, 38841 bytes |
| UI HTML all 9/9 checks | PASS |

The demo UI lives on the same FastAPI backend (port 8001), uses relative URLs,
and needs no CORS setup. Default limit=6 sent by the form is accepted by the
API (query param default). The full flow — tab display → form → API call →
result display → report link — works without any integration fixes.

## Verification Commands

Check PostgreSQL and pgvector:

```bash
./.venv/bin/python -m src.tender_research.cli check-db
```

Check embedding server reachability:

```bash
./.venv/bin/python -m src.tender_research.rag.cli check-embedding-server \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --base-url http://127.0.0.1:8090/v1
```

Build embeddings:

```bash
./.venv/bin/python -m src.tender_research.rag.cli build-embeddings \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --base-url http://127.0.0.1:8090/v1 \
  --limit 5000 \
  --batch-size 1
```

Search:

```bash
./.venv/bin/python -m src.tender_research.rag.cli search \
  --query "требования к содержанию и составу заявки" \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --base-url http://127.0.0.1:8090/v1 \
  --limit 5
```

Eval:

```bash
./.venv/bin/python -m src.tender_research.rag.cli eval \
  --questions tests/fixtures/tender_research/rag_eval_questions.json \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --base-url http://127.0.0.1:8090/v1 \
  --limit 5
```

Ask with local chat LLM:

```bash
./.venv/bin/python -m src.tender_research.rag.cli ask \
  --registry-number 0323100010326000013 \
  --question "Какие требования к составу заявки?" \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --base-url http://127.0.0.1:8090/v1 \
  --use-llm \
  --llm-base-url http://127.0.0.1:8088/v1 \
  --llm-model qwen2.5-14b \
  --limit 8
```

Analyze one tender into a markdown report:

```bash
./.venv/bin/python -m src.tender_research.rag.cli analyze-tender \
  --registry-number 0323100010326000013 \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --base-url http://127.0.0.1:8090/v1 \
  --use-llm \
  --llm-base-url http://127.0.0.1:8088/v1 \
  --llm-model /Users/master/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf \
  --limit 8 \
  --output data/rag/reports/analyze_tender_0323100010326000013.md
```
