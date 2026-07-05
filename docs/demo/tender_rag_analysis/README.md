# Демо: локальный AI-анализ закупки с источниками

## Что показывает демо

- Работа в закрытом локальном контуре (всё на Mac mini)
- Подготовка закупки к анализу (документы, чанки, эмбеддинги)
- Построение индекса по документам закупки
- Анализ документации локальной LLM с привязкой к источникам
- 10 разделов отчёта с citations
- Сохранение и повторный доступ к отчёту

## Demo URL

```
http://127.0.0.1:8001/demo/tender-agent
```

## Smoke registry number

```
0323100010326000013
```

## Expected result

| Check | Expected value |
|---|---|
| readiness | `ready_for_analysis=true` |
| prepare | `status=completed` |
| analyze | `status=completed`, `sections_count=10`, `sources_count>0` |
| report preview | не пустой |
| latest report | открывается, registry_number совпадает |

## Порядок чтения документации

1. [macmini_runtime_checklist.md](macmini_runtime_checklist.md) — что проверить перед запуском
2. [manual_demo_runbook.md](manual_demo_runbook.md) — пошаговый прогон на 5–7 минут
3. [customer_demo_script.md](customer_demo_script.md) — скрипт разговора с заказчиком
4. [demo_limitations.md](demo_limitations.md) — что не надо обещать
5. [troubleshooting.md](troubleshooting.md) — что делать, если что-то пошло не так
6. [next_mvp_steps.md](next_mvp_steps.md) — план следующего спринта
