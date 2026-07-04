# Local RAG Index For Tender Research

This repository now includes a local-only RAG layer for already downloaded and
extracted tender documents.

## Scope

- No cloud LLM dependency is required.
- No OCR is introduced.
- Only documents with `text_extraction_status=extracted` are chunked.
- Repeated indexing runs are idempotent for both chunks and embeddings.

## Data Model

The local RAG layer adds two SQL tables:

- `procurement_document_chunks`
- `procurement_document_embeddings`

Chunks keep the source document and tender linkage, character offsets, token
estimate, and source paths. Embeddings keep provider/model metadata and a
`vector_id` that points into the local vector store file.

## Commands

Build chunks:

```bash
python -m src.tender_research.rag.cli build-chunks --limit 100
```

Build embeddings:

```bash
python -m src.tender_research.rag.cli build-embeddings --limit 1000
```

Search:

```bash
python -m src.tender_research.rag.cli search \
  --query "требования к содержанию и составу заявки" \
  --limit 10
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
AI_CORP_RAG_EMBEDDINGS_PROVIDER=hashing
AI_CORP_RAG_EMBEDDINGS_MODEL=local-hash-v1
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
`hashing` provider remains available as the dependency-free fallback.

## Storage

Vectors are stored locally in a JSON vector store file under `data/rag/` by
default. This keeps the MVP dependency-free and portable across local
developer machines.

## Retrieval Mode

By default `ask` works in retrieval-only mode and prints the best matching
chunks. If `AI_CORP_RAG_USE_LLM=true` or `--use-llm` is passed, the CLI can
optionally call a local OpenAI-compatible endpoint and answer strictly from the
retrieved context.
