# План следующего MVP-спринта

## 1. Product next steps

- Выбор закупки из списка (не только по номеру)
- Страница истории анализов
- Отчёт в HTML/PDF
- Экспорт DOCX/PDF
- "Что проверить вручную" как отдельный checklist
- Риск-скоринг

## 2. Technical next steps

- Background jobs для prepare/analyze: выполнено в MVP через in-process runner + polling API
- Persistent run history в БД: выполнено
- Следующий шаг: production-grade queue (Celery / RQ / arq) или durable worker model
- Следующий шаг: push notifications через WebSocket/SSE вместо polling
- Улучшенное извлечение текста из документов
- OCR backlog (сканированные PDF)
- Извлечение таблиц
- Структурированный JSON output
- Ролевой доступ (admin / viewer / analyst)

## 3. Demo / customer next steps

- Подготовить 3–5 закупок разных типов для демо
- Сделать demo script под поставщика
- Сделать demo script под тендерный отдел
- Собрать обратную связь дизайн-партнёра

## 4. MVP proposal (ближайший спринт)

**Вариант A: "Экспорт отчёта"**
- HTML/DOCX/PDF export
- скачивание отчёта в customer-friendly формате
- шаблон executive summary

**Вариант B: "Production queue"**
- durable background workers
- retry policy
- stale job reconciliation после restart
- WebSocket / SSE уведомления

**Вариант C: "Выбор закупки и улучшенный UI"**
- список доступных закупок
- поиск по номеру/названию
- улучшенная навигация по отчёту
