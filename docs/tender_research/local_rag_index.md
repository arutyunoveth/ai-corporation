# Local RAG Index For Tender Research

Mac mini is now the source of truth for Arvectum runtime data. PostgreSQL +
pgvector is the server-side database, while SQLite remains the fast default for
dev and tests. The local RAG layer sits on top of already downloaded and
extracted tender documents and keeps vectors in provider/model-specific JSON
stores under `data/rag/`.

## Scope

- No cloud LLM dependency is required.
- No OCR is introduced.
- Only documents with `text_extraction_status=extracted` are chunked.
- Repeated indexing runs are idempotent for both chunks and embeddings.
- `local_hash` stays available as a smoke/test fallback.
- `llama.cpp` embeddings are the preferred local production path.

## Data Model

The local RAG layer uses:

- `procurement_document_chunks`
- `procurement_document_embeddings`

Chunks keep the source document and tender linkage, character offsets, token
estimate, and source paths. Embeddings keep provider/model metadata and a
`vector_id` that points into a provider/model-specific local vector store file.

## Recommended Models

- First production-style local embedding model: `Qwen3-Embedding-4B`
- Benchmark comparison model: `BGE-M3`
- Heavy test / future benchmark: `Qwen3-Embedding-8B`
- Smoke/test fallback only: `local-hash-v1`

## Embedding Server Layout

Keep chat and embeddings as separate local services on Mac mini:

1. Chat / reasoning server
   `http://127.0.0.1:8088/v1`
2. Embedding server
   `http://127.0.0.1:8090/v1`

Example embedding server commands:

```bash
llama-server \
  --model /Users/master/models/embeddings/Qwen3-Embedding-4B-Q8_0.gguf \
  --embedding \
  --ctx-size 8192 \
  --port 8090
```

```bash
llama-server \
  --model /Users/master/models/embeddings/bge-m3-Q8_0.gguf \
  --embedding \
  --ctx-size 8192 \
  --port 8090
```

Pooling depends on both the model and the current `llama.cpp` build. Do not
hardcode pooling in application config. Keep the exact launch command in a
local runbook, not in `.env` and not in git-tracked secrets.

## Commands

Build chunks:

```bash
python -m src.tender_research.rag.cli build-chunks --limit 100
```

Check the embedding server:

```bash
python -m src.tender_research.rag.cli check-embedding-server \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --base-url http://127.0.0.1:8090/v1
```

Build embeddings with the smoke fallback:

```bash
python -m src.tender_research.rag.cli build-embeddings \
  --provider local_hash \
  --model local-hash-v1 \
  --limit 1000
```

Build embeddings with `llama.cpp`:

```bash
python -m src.tender_research.rag.cli build-embeddings \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --base-url http://127.0.0.1:8090/v1 \
  --batch-size 16 \
  --limit 5000
```

Search:

```bash
python -m src.tender_research.rag.cli search \
  --query "требования к содержанию и составу заявки" \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --limit 10
```

Eval:

```bash
python -m src.tender_research.rag.cli eval \
  --questions tests/fixtures/tender_research/rag_eval_questions.json \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --limit 5
```

Ask one registry number without LLM:

```bash
python -m src.tender_research.rag.cli ask \
  --registry-number 0373200027426001278 \
  --question "Какие требования к составу заявки?"
```

## Configuration

Supported environment variables:

```bash
AI_CORP_RAG_CHUNK_SIZE_CHARS=1500
AI_CORP_RAG_CHUNK_OVERLAP_CHARS=200
AI_CORP_RAG_MIN_CHUNK_CHARS=120
AI_CORP_RAG_EMBEDDINGS_PROVIDER=local_hash
AI_CORP_RAG_EMBEDDINGS_MODEL=local-hash-v1
AI_CORP_RAG_EMBEDDINGS_BASE_URL=http://127.0.0.1:8090/v1
AI_CORP_RAG_EMBEDDINGS_TIMEOUT_SECONDS=60
AI_CORP_RAG_EMBEDDINGS_BATCH_SIZE=16
AI_CORP_RAG_EMBEDDINGS_DIMENSION=auto
AI_CORP_RAG_VECTOR_STORE=json
AI_CORP_RAG_VECTOR_STORE_PATH=./data/rag/vector_store.json
AI_CORP_RAG_USE_LLM=false
AI_CORP_LOCAL_LLM_BASE_URL=http://127.0.0.1:8088/v1
AI_CORP_LOCAL_LLM_MODEL=qwen2.5-14b
```

### Optional sentence-transformers mode

The code also supports:

```bash
AI_CORP_RAG_EMBEDDINGS_PROVIDER=sentence_transformers
AI_CORP_RAG_EMBEDDINGS_MODEL=intfloat/multilingual-e5-small
```

This mode requires the `sentence-transformers` package to be installed locally.
If it is not installed, the CLI will fail with a clear error and the local
`local_hash` provider remains available as the dependency-free fallback.

## Storage

Vectors are stored locally in JSON files under `data/rag/` by default. The
default `local_hash` path remains compatible with the existing MVP store, while
other providers/models use namespaced files so their embeddings do not
overwrite each other.

Eval results are written as JSONL under `data/rag/eval/`.

## Retrieval Mode

By default `ask` works in retrieval-only mode and prints the best matching
chunks. If `AI_CORP_RAG_USE_LLM=true` or `--use-llm` is passed, the CLI can
optionally call a local OpenAI-compatible chat endpoint and answer strictly
from the retrieved context.

## Known Limitations

- `local_hash` is not semantic and should only be treated as a smoke provider.
- `llama.cpp` availability is external to the test suite and must be checked via
  `check-embedding-server`.
- Pooling behavior depends on the model and the current `llama.cpp` build.
- Output dimension for some GGUF embedding models may still depend on runtime
  behavior rather than a fixed CLI flag.
- Eval currently reports retrieval outputs and simple summary stats only; it
  does not run an automatic judge.
