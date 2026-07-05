# План следующего MVP-спринта

## 1. Product next steps

- Выбор закупки из списка (не только по номеру)
- Страница истории анализов
- Отчёт в HTML/PDF
- Экспорт DOCX/PDF
- "Что проверить вручную" как отдельный checklist
- Риск-скоринг

## 2. Technical next steps

- Background jobs для prepare/analyze (Celery / RQ / arq)
- Progress polling через WebSocket или polling endpoint
- Persistent run history в БД
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

**Вариант A: "История анализов и экспорт отчёта"**
- persist runs
- список предыдущих анализов
- просмотр/скачивание отчёта DOCX/PDF

**Вариант B: "Фоновая подготовка закупки с прогрессом"**
- async prepare
- background task queue
- progress polling в UI
- WebSocket / SSE уведомления

**Вариант C: "Выбор закупки и улучшенный UI"**
- список доступных закупок
- поиск по номеру/названию
- улучшенная навигация по отчёту
