# Демо-пакет: AI-агент Арвектум для анализа закупки

Короткий пакет для ручного показа локального AI-агента Арвектум клиенту, дизайн-партнёру или внутренней команде.

## Что это за демо

Локальный AI-агент Арвектум помогает быстро разобрать закупку: проверить готовность данных, запустить анализ в background job, показать прогресс по разделам, открыть структурированный отчёт и скачать его в DOCX/PDF.

## Что показывает демо

- загрузку и подготовку закупки к анализу;
- локальный анализ без облачных LLM;
- progress по секциям без зависания UI;
- структурированный отчёт по 10 разделам;
- историю запусков;
- экспорт DOCX/PDF.

## Для кого это демо

- поставщики;
- тендерные отделы;
- руководители продаж и закупок;
- дизайн-партнёры пилота.

## Что нужно для запуска

- Mac mini;
- PostgreSQL + pgvector;
- embedding server `http://127.0.0.1:8090/v1`;
- LLM server `http://127.0.0.1:8088/v1`;
- backend `http://127.0.0.1:8001`;
- demo URL: `http://127.0.0.1:8001/demo/tender-agent`.

## Главный сценарий

- registry_number: `0323100010326000013`
- preset: `Mac mini: локальная LLM + Qwen3 embeddings`
- mode: `fast / Быстрый`

## Подробные инструкции

1. [manual_demo_runbook.md](manual_demo_runbook.md) — пошаговый ручной прогон.
2. [customer_demo_script.md](customer_demo_script.md) — готовый сценарий разговора на 5–7 минут.
3. [macmini_runtime_checklist.md](macmini_runtime_checklist.md) — быстрая проверка перед созвоном.
4. [troubleshooting.md](troubleshooting.md) — что делать, если что-то пошло не так.
5. [demo_limitations.md](demo_limitations.md) — как честно объяснять ограничения.
6. [customer_demo_boundaries.md](customer_demo_boundaries.md) — что показываем и чего не обещаем.
7. [client_onepager.md](client_onepager.md) — one-pager после звонка.
