# Следующие шаги MVP

## Уже выполнено в текущем MVP

- background jobs / progress;
- fast / balanced / detailed analysis modes;
- lexical fallback retrieval;
- DOCX / PDF export.

## Ближайшие возможные спринты

### 1. Брендирование DOCX/PDF отчёта под Арвектум

- логотип;
- фирменные цвета;
- титульная страница;
- аккуратные таблицы;
- footer с `arvectum.com`.

### 2. Production queue

- Celery / RQ / Redis или другой runner;
- job recovery after restart;
- concurrent jobs.

### 3. User / project workspace

- привязка анализов к клиенту или проекту;
- фильтрация истории запусков.

### 4. Качество анализа

- better section prompts;
- risk scoring;
- decision memo;
- supplier fit.

### 5. Интеграции

- импорт из ЕИС;
- API для внешних систем;
- экспорт в CRM или документооборот.

## Зачем это важно

Дорожная карта показывает, что MVP уже собран в управляемый контур, а следующие шаги понятны и отделены от текущего демо.
