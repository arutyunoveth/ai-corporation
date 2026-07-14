# Ручная приемка R2

Для каждого номера заполнить по исходному архиву ЕИС и сопоставить с `report.json`, `report.html`, DOCX и PDF.

| Проверка | electrical-1 | electrical-2 | goods | service | complex |
|---|---|---|---|---|---|
| Предмет закупки | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED |
| НМЦК | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED |
| Сроки | REVIEW | REVIEW | REVIEW | REVIEW | REVIEW |
| Все позиции | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED |
| Количество и единицы | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED |
| Цены | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED |
| Обязательные документы | REVIEW | REVIEW | REVIEW | REVIEW | REVIEW |
| Договорные риски | REVIEW | REVIEW | REVIEW | REVIEW | REVIEW |
| Evidence на каждый существенный вывод | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED | MATCH_NORMALIZED |
| Нет придуманных фактов | PASS | PASS | PASS | PASS | PASS |
| Статус needs_review/go/no_go корректен | PASS | PASS | PASS | PASS | PASS |

Критическая ошибка в любой строке означает BLOCKED до исправления и повторного прогона. Детали построчной сверки — в [`../r2/R2_LINE_ITEM_AUDIT.csv`](../r2/R2_LINE_ITEM_AUDIT.csv).

## Метрики

Автоматическое время из прогона: 1.47 / 1.88 / 2.14 / 3.40 / 2.92 с соответственно. Время ручной проверки, исправления пользователя и оставшиеся вопросы должны быть внесены после проверки оператором; автоматически придумывать эти значения нельзя.
