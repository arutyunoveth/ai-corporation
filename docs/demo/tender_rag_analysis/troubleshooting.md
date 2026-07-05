# Troubleshooting

## 1. UI не открывается

Проверить:

```bash
curl http://127.0.0.1:8001/demo/tender-agent
```

Если не открывается:
- backend не запущен → перезапустить
- неправильный порт → проверить `lsof -i :8001`
- backend смотрит не туда → проверить логи

## 2. Health не отвечает

```bash
curl http://127.0.0.1:8001/api/tender-research/health
```

Если ошибка:
- backend не запущен
- неправильный `AI_CORP_DATABASE_URL`
- PostgreSQL не запущен

## 3. `no_context` при analyze

Причины:
- закупки нет в БД
- нет chunks
- нет embeddings
- backend смотрит не в ту БД

Проверить:

```bash
python -m src.tender_research.cli check-db
```

И:

```bash
curl http://127.0.0.1:8001/api/tender-research/prepare/0323100010326000013/status
```

## 4. Embedding server недоступен

```bash
python -m src.tender_research.rag.cli check-embedding-server \
  --provider llama_cpp \
  --model Qwen3-Embedding-4B \
  --base-url http://127.0.0.1:8090/v1
```

## 5. Chat LLM server недоступен

```bash
curl -s http://127.0.0.1:8088/v1/models
```

## 6. Report link не открывается

```bash
curl http://127.0.0.1:8001/api/tender-research/analyze/0323100010326000013/latest
```

Для history/report-by-run:

```bash
curl "http://127.0.0.1:8001/api/tender-research/analyze/history?registry_number=0323100010326000013&limit=5"
curl http://127.0.0.1:8001/api/tender-research/analyze/history/<run_id>/report
```

## 7. Backend смотрит не в ту БД

Проверить:
- `python -m src.tender_research.cli check-db`
- API health `can_connect`
- `AI_CORP_DATABASE_URL` — правильный порт (55432, не 5432)

## 8. Тесты неожиданно запускают live network

Напомнить: default pytest offline. Live профили только по флагам:

```
--run-integration
--run-postgres
--run-network
--run-llama-cpp
--run-live-smoke
```

## 9. Background job завис в `running`

Проверить:

```bash
curl http://127.0.0.1:8001/api/tender-research/jobs/<job_id>
```

Если backend был перезапущен во время выполнения:
- для MVP это известное ограничение;
- job metadata остаётся в БД;
- активная in-process задача не возобновляется автоматически;
- нужно перезапустить prepare/analyze job вручную.

## 10. UI долго показывает polling

Это ожидаемо для новой закупки, если идут:
- загрузка документов;
- text extraction;
- chunks;
- embeddings;
- LLM section analysis.

Если polling превысил ~10 минут:
- проверить `/api/tender-research/jobs/<job_id>`;
- проверить backend logs;
- повторно проверить `health`, embedding server и LLM server.
