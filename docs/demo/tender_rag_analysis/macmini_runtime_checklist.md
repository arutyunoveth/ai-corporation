# Mac mini Runtime Checklist

Проверить перед демо.

## A. Backend health

```bash
curl http://127.0.0.1:8001/api/tender-research/health
```

Ожидаем:
- HTTP 200
- `database_url_masked` без пароля
- `can_connect=true`
- `table_counts` не пуст

## B. Embedding server

```bash
python -m src.tender_research.rag.cli check-embedding-server \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --base-url http://127.0.0.1:8090/v1
```

Ожидаем:
- `reachable=true`
- `dimension=2560`

## C. Chat LLM server

```bash
curl -s http://127.0.0.1:8088/v1/models
```

Ожидаем:
- server reachable
- model list содержит `/Users/master/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf`

## D. Database

```bash
export AI_CORP_DATABASE_URL='postgresql+psycopg://arvectum:<PASSWORD>@127.0.0.1:55432/arvectum'
python -m src.tender_research.cli check-db
```

Ожидаем:
- `can_connect=true`
- таблицы присутствуют

## E. Demo UI

Открыть в браузере:

```
http://127.0.0.1:8001/demo/tender-agent
```

Ожидаем:
- страница загружается
- вкладка "Анализ закупки" присутствует
- кнопки "Проверить готовность", "Подготовить закупку к анализу", "Проанализировать закупку" видны

## F. Быстрый API precheck

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

Ожидаем:
- HTTP 200
- `status=completed`
- `sections_count=10`
- `sources_count>0`
- `report_path` не пуст

## G. Если что-то не работает

Перейти к [troubleshooting.md](troubleshooting.md).
