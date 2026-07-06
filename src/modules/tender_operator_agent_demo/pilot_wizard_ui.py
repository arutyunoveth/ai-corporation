from __future__ import annotations


def render_tender_operator_pilot_wizard_html() -> str:
    return """
    <html lang="ru">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Пилот тендерного агента</title>
        <style>
          :root {
            --bg: #04152f;
            --bg-soft: #0b2347;
            --panel: rgba(255, 255, 255, 0.08);
            --panel-strong: rgba(255, 255, 255, 0.12);
            --line: rgba(193, 220, 255, 0.14);
            --text: #f5fbff;
            --muted: rgba(245, 251, 255, 0.72);
            --mint: #59f0cf;
            --mint-strong: #00c8a0;
            --danger: #ff8f9d;
            --warning: #ffc96b;
            --shadow: 0 32px 80px rgba(1, 14, 34, 0.34);
          }
          * { box-sizing: border-box; }
          body {
            margin: 0;
            font-family: "PT Sans", Arial, sans-serif;
            color: var(--text);
            background:
              radial-gradient(circle at top left, rgba(89, 240, 207, 0.16), transparent 24%),
              radial-gradient(circle at right top, rgba(119, 182, 255, 0.16), transparent 26%),
              linear-gradient(180deg, #031127 0%, #04152f 56%, #0a1f42 100%);
          }
          .page {
            width: min(1320px, calc(100vw - 28px));
            margin: 0 auto;
            padding: 16px 0 42px;
          }
          .hero {
            border: 1px solid var(--line);
            border-radius: 30px;
            padding: 14px 18px;
            background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
            box-shadow: var(--shadow);
            overflow: hidden;
            position: relative;
          }
          .hero::after {
            content: "";
            position: absolute;
            inset: auto -120px -160px auto;
            width: 320px;
            height: 320px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(89, 240, 207, 0.18), transparent 66%);
            pointer-events: none;
          }
          .brand-row {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 10px;
          }
          .brand-logo {
            width: 72px;
            height: 72px;
            display: block;
            flex: 0 0 auto;
          }
          .hero-top {
            display: block;
          }
          .hero-copy {
            max-width: 920px;
            min-width: 0;
          }
          h1 {
            margin: 0 0 8px;
            font-size: clamp(14px, 2.2vw, 34px);
            line-height: 1.02;
            letter-spacing: -0.02em;
            white-space: nowrap;
          }
          .subtitle {
            margin: 0;
            color: var(--muted);
            line-height: 1.35;
            font-size: 14px;
            max-width: 720px;
          }
          .link-button, .button {
            appearance: none;
            border: 1px solid rgba(255,255,255,0.14);
            color: var(--text);
            background: rgba(255,255,255,0.06);
            border-radius: 999px;
            min-height: 46px;
            padding: 0 18px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font: inherit;
          }
          .button.primary, .link-button.primary {
            background: linear-gradient(135deg, rgba(0, 200, 160, 0.22), rgba(89, 240, 207, 0.12));
            border-color: rgba(89, 240, 207, 0.3);
          }
          .hero-badges {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 12px;
          }
          .badge {
            padding: 7px 11px;
            border-radius: 999px;
            border: 1px solid rgba(89, 240, 207, 0.22);
            background: rgba(89, 240, 207, 0.08);
            color: var(--mint);
            font-size: 12px;
          }
          .layout {
            margin-top: 18px;
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 18px;
          }
          .stack {
            display: grid;
            gap: 18px;
            align-content: start;
          }
          .card {
            border: 1px solid var(--line);
            border-radius: 24px;
            background: var(--panel);
            padding: 22px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.14);
          }
          .card h2, .card h3 {
            margin: 0 0 14px;
          }
          .card p {
            margin: 0;
            color: var(--muted);
            line-height: 1.55;
          }
          .step-card {
            position: relative;
            overflow: hidden;
          }
          .step-chip {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 36px;
            height: 36px;
            border-radius: 999px;
            background: rgba(89, 240, 207, 0.14);
            color: var(--mint);
            font-weight: 700;
            margin-bottom: 14px;
          }
          .field-grid {
            display: grid;
            gap: 14px;
          }
          .field-grid.two {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .field-grid.three {
            grid-template-columns: 1.1fr 1.5fr 1fr;
          }
          label {
            display: grid;
            gap: 8px;
            color: var(--text);
            font-size: 15px;
          }
          .label-title {
            font-weight: 700;
          }
          .label-hint {
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
          }
          input, textarea, select {
            width: 100%;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            background: rgba(255,255,255,0.06);
            color: var(--text);
            padding: 13px 14px;
            font: inherit;
          }
          textarea {
            min-height: 108px;
            resize: vertical;
          }
          input[type="file"] {
            padding: 12px;
            background: rgba(255,255,255,0.04);
          }
          .notice {
            margin-top: 12px;
            padding: 12px 14px;
            border-radius: 16px;
            background: rgba(255, 201, 107, 0.1);
            border: 1px solid rgba(255, 201, 107, 0.18);
            color: #ffe3a8;
            font-size: 14px;
            line-height: 1.5;
          }
          .actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 18px;
          }
          .flash {
            border-radius: 18px;
            padding: 14px 16px;
            line-height: 1.5;
            font-size: 14px;
            background: rgba(89, 240, 207, 0.12);
            border: 1px solid rgba(89, 240, 207, 0.18);
          }
          .flash.error {
            background: rgba(255, 143, 157, 0.12);
            border-color: rgba(255, 143, 157, 0.2);
            color: #ffd2d9;
          }
          .result-shell {
            display: grid;
            gap: 18px;
          }
          .search-grid {
            display: grid;
            gap: 14px;
          }
          .search-toolbar {
            display: grid;
            gap: 10px;
            padding: 16px;
            border-radius: 20px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
          }
          .search-toolbar-row.simple {
            grid-template-columns: minmax(0, 1fr) auto auto;
            align-items: end;
          }
          .search-toolbar-row {
            display: grid;
            gap: 10px;
            align-items: end;
          }
          .search-toolbar-row.primary {
            grid-template-columns: 190px minmax(0, 1.65fr) minmax(0, 1fr);
          }
          .search-toolbar-row.secondary,
          .search-toolbar-row.tertiary {
            grid-template-columns: repeat(4, minmax(0, 1fr));
          }
          .search-toolbar-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            margin-top: 2px;
          }
          .search-advanced {
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.03);
            overflow: hidden;
          }
          .search-advanced summary {
            list-style: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 14px 16px;
            font-weight: 700;
            user-select: none;
          }
          .search-advanced summary::-webkit-details-marker {
            display: none;
          }
          .search-advanced summary::after {
            content: "Показать";
            color: var(--muted);
            font-weight: 400;
            font-size: 13px;
          }
          .search-advanced[open] summary::after {
            content: "Скрыть";
          }
          .search-advanced-body {
            display: grid;
            gap: 10px;
            padding: 0 16px 16px;
          }
          .search-toolbar-note {
            color: var(--muted);
            font-size: 13px;
            line-height: 1.4;
          }
          .search-results {
            display: grid;
            gap: 10px;
            margin-top: 16px;
          }
          .search-results-board {
            display: grid;
            gap: 10px;
          }
          .search-results-header {
            display: flex;
            gap: 14px;
            align-items: center;
            justify-content: space-between;
            padding: 0 4px;
          }
          .search-results-headline {
            display: grid;
            gap: 4px;
          }
          .search-results-title {
            font-size: 18px;
            font-weight: 700;
          }
          .search-results-note {
            color: var(--muted);
            font-size: 13px;
            line-height: 1.4;
          }
          .search-results-tools {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
          }
          .search-results-footer {
            display: flex;
            gap: 12px;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            padding: 4px 4px 0;
          }
          .search-results-pagination {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
          }
          .search-results-count {
            color: var(--muted);
            font-size: 13px;
            line-height: 1.4;
          }
          .search-list-head {
            display: grid;
            grid-template-columns: minmax(0, 2.55fr) minmax(220px, 1.1fr) minmax(180px, 0.8fr) auto;
            gap: 14px;
            padding: 0 16px;
            color: rgba(245, 251, 255, 0.6);
            font-size: 11px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
          }
          .search-card {
            padding: 16px;
            border-radius: 20px;
            background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.04));
            border: 1px solid rgba(255,255,255,0.09);
            display: grid;
            grid-template-columns: minmax(0, 2.55fr) minmax(220px, 1.1fr) minmax(180px, 0.8fr) auto;
            gap: 14px;
            align-items: start;
          }
          .search-card-main {
            min-width: 0;
          }
          .search-number {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
            color: var(--mint);
            text-decoration: none;
            font-weight: 700;
          }
          .search-number:hover {
            color: #87ffe5;
          }
          .search-card h3 {
            margin: 0;
            font-size: 17px;
            line-height: 1.32;
          }
          .search-card-meta {
            display: grid;
            gap: 8px;
            align-content: start;
          }
          .search-meta-item {
            padding: 11px 12px;
            border-radius: 14px;
            background: rgba(255,255,255,0.045);
            border: 1px solid rgba(255,255,255,0.06);
          }
          .search-meta-item .metric-value {
            font-size: 15px;
          }
          .search-price-box {
            padding: 13px 14px;
            border-radius: 16px;
            background: rgba(89, 240, 207, 0.08);
            border: 1px solid rgba(89, 240, 207, 0.18);
            display: grid;
            gap: 10px;
          }
          .search-price-box .metric-value {
            font-size: 20px;
          }
          .search-relevance {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            width: fit-content;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.05);
          }
          .search-relevance.high {
            color: #8ff8cf;
            border-color: rgba(89, 240, 207, 0.28);
            background: rgba(89, 240, 207, 0.12);
          }
          .search-relevance.medium {
            color: #ffe3a8;
            border-color: rgba(255, 201, 107, 0.26);
            background: rgba(255, 201, 107, 0.1);
          }
          .search-relevance.low, .search-relevance.not_recommended {
            color: #ffd2d9;
            border-color: rgba(255, 143, 157, 0.24);
            background: rgba(255, 143, 157, 0.1);
          }
          .search-badges {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 10px;
          }
          .search-badge {
            padding: 7px 11px;
            border-radius: 999px;
            background: rgba(89, 240, 207, 0.1);
            border: 1px solid rgba(89, 240, 207, 0.18);
            color: var(--mint);
            font-size: 12px;
          }
          .search-actions {
            display: grid;
            gap: 10px;
            align-content: start;
            justify-items: end;
            min-width: 170px;
          }
          .search-actions .button,
          .search-actions .link-button,
          .search-actions .search-report-slot {
            min-width: 170px;
          }
          .search-actions .search-report-slot {
            display: grid;
            gap: 10px;
          }
          .selected-procurement {
            margin-top: 14px;
            padding: 14px 16px;
            border-radius: 16px;
            background: rgba(89, 240, 207, 0.12);
            border: 1px solid rgba(89, 240, 207, 0.2);
            color: var(--text);
          }
          .selected-procurement strong {
            display: block;
            margin-bottom: 6px;
          }
          .metrics {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
          }
          .metric {
            padding: 14px;
            border-radius: 18px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
          }
          .metric-label {
            display: block;
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
          }
          .metric-value {
            display: block;
            font-size: 18px;
            line-height: 1.35;
          }
          .result-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
          }
          .result-block {
            padding: 16px;
            border-radius: 20px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
          }
          .result-block h3 {
            margin: 0 0 12px;
            font-size: 18px;
          }
          .result-block ul {
            margin: 0;
            padding-left: 18px;
            color: var(--muted);
            line-height: 1.55;
          }
          .timeline {
            display: grid;
            gap: 10px;
          }
          .timeline-item {
            padding: 12px 14px;
            border-radius: 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
          }
          .timeline-title {
            font-weight: 700;
            margin-bottom: 4px;
          }
          .timeline-state {
            color: var(--mint);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
          }
          .timeline-note {
            color: var(--muted);
            font-size: 14px;
            line-height: 1.45;
            margin-top: 6px;
          }
          .status-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: 14px 0 0;
          }
          .status-chip {
            padding: 8px 12px;
            border-radius: 999px;
            font-size: 12px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.05);
          }
          .empty {
            color: var(--muted);
            line-height: 1.6;
          }
          @media (max-width: 980px) {
            .layout, .field-grid.two, .field-grid.three, .result-grid, .metrics, .search-toolbar-row.simple, .search-toolbar-row.primary, .search-toolbar-row.secondary, .search-toolbar-row.tertiary {
              grid-template-columns: 1fr;
            }
            .hero-top {
              flex-direction: column;
            }
            .search-list-head,
            .search-card {
              grid-template-columns: 1fr;
            }
            .search-actions {
              justify-items: stretch;
              min-width: 0;
            }
            .search-actions .button,
            .search-actions .link-button,
            .search-actions .search-report-slot {
              min-width: 0;
            }
            .search-results-header,
            .search-toolbar-actions {
              align-items: flex-start;
              flex-direction: column;
            }
          }
        </style>
      </head>
      <body>
        <div class="page">
          <section class="hero">
            <div class="brand-row">
              <img class="brand-logo" src="/demo/tender-agent/assets/arvectum-logo-block.svg" alt="Arvectum" />
            </div>
            <div class="hero-top">
              <div class="hero-copy">
                <h1>Прогон тендера через формы, а не через `.md`</h1>
                <p class="subtitle">
                  Найдите закупку по фильтрам или вставьте ссылку ЕИС. Обработка запускается прямо из карточки результата поиска.
                </p>
                <div class="hero-badges">
                  <span class="badge">44-ФЗ, 223-ФЗ и капремонт</span>
                  <span class="badge">Обработка из списка результатов</span>
                  <span class="badge">Ручной контроль сохранен</span>
                </div>
              </div>
            </div>
          </section>

          <div class="layout">
            <main class="stack">
              <form id="pilot-form" class="stack">
                <section class="card step-card">
                  <h2>Найдите закупку или вставьте ссылку / реестровый номер</h2>
                  <div class="notice" style="margin-bottom:16px">
                    Система не отправляет письма поставщикам, не подает заявку и
                    не подписывает документы. Финальное решение всегда остается у
                    человека.
                  </div>
                  <div class="field-grid" style="margin-bottom:14px">
                    <label>
                      <span class="label-title">Ссылка на закупку в ЕИС или реестровый номер</span>
                      <span class="label-hint">Поддерживается ссылка вида `zakupki.gov.ru/...regNumber=...` или просто номер закупки. Это поле используется как основной вход в сценарий.</span>
                      <input name="procurement_url" placeholder="https://zakupki.gov.ru/epz/order/notice/ea44/view.html?regNumber=0888200000224000038" />
                    </label>
                  </div>
                  <div id="selected-procurement" class="selected-procurement" style="display:none"></div>
                  <div class="search-grid">
                    <h3 style="margin:8px 0 0">Поиск закупки по ключевым словам и фильтрам</h3>
                    <div class="search-toolbar">
                      <div class="search-toolbar-row simple">
                        <label>
                          <span class="label-title">Ключевые слова</span>
                          <input name="search_query" placeholder="Например: обучение информационная безопасность" />
                        </label>
                        <button class="button" id="search-button" type="button">Найти закупки</button>
                        <button class="button" id="search-reset-button" type="button">Сбросить фильтры</button>
                      </div>
                      <details class="search-advanced">
                        <summary>Расширенные фильтры</summary>
                        <div class="search-advanced-body">
                          <div class="search-toolbar-note">Как в тендерных сервисах: сначала быстрый поиск по ключевым словам, затем при необходимости сужаем выборку фильтрами.</div>
                          <div class="search-toolbar-row primary">
                            <label>
                              <span class="label-title">Категория закупки</span>
                              <select name="search_law">
                                <option value="44fz">44-ФЗ</option>
                                <option value="223fz">223-ФЗ</option>
                                <option value="capital_repair">Капремонт</option>
                              </select>
                            </label>
                            <label>
                              <span class="label-title">Регион</span>
                              <input name="search_region" placeholder="Например: Хабаровский край" />
                            </label>
                            <div></div>
                          </div>
                          <div class="search-toolbar-row secondary">
                            <label>
                              <span class="label-title">Статус закупки</span>
                              <select name="search_status">
                                <option value="">Любой статус</option>
                                <option value="Подача заявок">Подача заявок</option>
                                <option value="Работа комиссии">Работа комиссии</option>
                                <option value="Закупка завершена">Закупка завершена</option>
                              </select>
                            </label>
                            <label>
                              <span class="label-title">Способ закупки</span>
                              <select name="search_procedure_type">
                                <option value="">Любой способ</option>
                                <option value="Электронный аукцион">Электронный аукцион</option>
                                <option value="Запрос котировок">Запрос котировок</option>
                                <option value="Открытый конкурс">Открытый конкурс</option>
                                <option value="Электронный конкурс">Электронный конкурс</option>
                                <option value="Запрос предложений">Запрос предложений</option>
                              </select>
                            </label>
                            <label>
                              <span class="label-title">Дата публикации: от</span>
                              <input name="search_date_from" type="date" />
                            </label>
                            <label>
                              <span class="label-title">Дата публикации: до</span>
                              <input name="search_date_to" type="date" />
                            </label>
                          </div>
                          <div class="search-toolbar-row tertiary">
                            <label>
                              <span class="label-title">Срок подачи: от</span>
                              <input name="search_deadline_from" type="date" />
                            </label>
                            <label>
                              <span class="label-title">Срок подачи: до</span>
                              <input name="search_deadline_to" type="date" />
                            </label>
                            <label>
                              <span class="label-title">НМЦК: от</span>
                              <input name="search_price_from" type="number" min="0" step="1" placeholder="Например: 500000" />
                            </label>
                            <label>
                              <span class="label-title">НМЦК: до</span>
                              <input name="search_price_to" type="number" min="0" step="1" placeholder="Например: 5000000" />
                            </label>
                          </div>
                        </div>
                      </details>
                    </div>
                    <div id="search-flash" class="flash" style="display:none"></div>
                    <div id="search-results" class="search-results empty">
                      Введите ключевые слова и при необходимости уточните фильтры. Результаты поиска появятся здесь.
                    </div>
                    <div class="form-actions" style="margin-top:12px">
                      <button class="button" id="search-demo-button" type="button">Открыть демо-закупку 0323100010326000013</button>
                    </div>
                  </div>
                </section>

                <section class="card step-card">
                  <h2>Какие базовые ограничения по экономике и сделке?</h2>
                  <div class="field-grid two">
                    <label>
                      <span class="label-title">Целевая маржа, %</span>
                      <input name="target_margin_percent" type="number" step="0.1" min="0" max="95" value="15" />
                    </label>
                    <label>
                      <span class="label-title">Отсрочка оплаты, дней</span>
                      <input name="payment_delay_days" type="number" step="1" min="0" max="365" value="45" />
                    </label>
                  </div>
                  <div class="field-grid two" style="margin-top:14px">
                    <label>
                      <span class="label-title">Резерв логистики, %</span>
                      <input name="logistics_reserve_percent" type="number" step="0.1" min="0" max="95" value="3" />
                    </label>
                    <label>
                      <span class="label-title">Резерв риска, %</span>
                      <input name="risk_reserve_percent" type="number" step="0.1" min="0" max="95" value="5" />
                    </label>
                  </div>
                </section>

                <section class="card step-card">
                  <h2>Дозагрузите документы, если хотите усилить анализ</h2>
                  <div class="field-grid">
                    <label>
                      <span class="label-title">Файл извещения</span>
                      <span class="label-hint">Используйте, если нужно усилить контекст извещения или заменить неполный автоподхват.</span>
                      <input id="notice-files" type="file" multiple />
                    </label>
                    <label>
                      <span class="label-title">Файл ТЗ / техническая спецификация</span>
                      <span class="label-hint">Таблицы из этого блока больше не считаются ТКП только потому, что в них есть цены.</span>
                      <input id="technical-files" type="file" multiple />
                    </label>
                    <label>
                      <span class="label-title">Файл проекта договора</span>
                      <span class="label-hint">Добавьте, если проект договора не подтянулся автоматически или нужен более точный анализ условий.</span>
                      <input id="contract-files" type="file" multiple />
                    </label>
                  </div>
                </section>

                <section class="card step-card">
                  <h2>Добавьте КП и дополнительные файлы, если они уже есть</h2>
                  <div class="field-grid">
                    <label>
                      <span class="label-title">Коммерческие предложения поставщиков</span>
                      <input id="quote-files" type="file" multiple />
                    </label>
                    <label>
                      <span class="label-title">Дополнительные файлы</span>
                      <input id="supporting-files" type="file" multiple />
                    </label>
                  </div>
                </section>

                <section class="card step-card">
                  <h2>Запустить обработку</h2>
                  <p>
                    Интерфейс сам создаст run, добавит документы в нужной роли,
                    выполнит анализ и покажет итоговый статус.
                  </p>
                  <div id="wizard-flash" class="flash" style="display:none"></div>
                  <div class="actions">
                    <button class="button primary" id="process-button" type="submit">Обработать тендер</button>
                    <button class="button" id="reset-button" type="button">Очистить форму</button>
                  </div>
                </section>
              </form>

              <section class="card">
                <h2>Результат обработки</h2>
                <div id="result-root" class="empty">
                  Заполните форму слева, нажмите «Обработать тендер», и здесь появятся статус, шаги пайплайна, краткая рекомендация и ссылки на отчет.
                </div>
              </section>
            </main>
          </div>
        </div>

        <script>
          const STEP_LABELS = {
            documents: 'Документы',
            requirements: 'Требования',
            questions: 'Вопросы',
            rfq: 'RFQ',
            quotes: 'ТКП',
            economics: 'Экономика',
            risks: 'Риски',
            decision: 'Решение',
          };
          const STATUS_LABELS = {
            uploaded: 'загружено',
            docs_required: 'нужна загрузка документов',
            ready_to_analyze: 'готово к анализу',
            analyzing: 'анализируется',
            completed: 'завершено',
            completed_with_warnings: 'завершено с ограничениями',
            failed: 'ошибка',
            needs_review: 'нужна проверка',
            pending: 'ожидает',
            running: 'в работе',
            done: 'выполнено',
            partial: 'частично',
            warning: 'риск',
            blocked: 'заблокировано',
          };
          const SEARCH_PAGE_SIZE = 10;
          const fileRolePrefixes = {
            notice: 'notice',
            technical: 'technical_spec',
            contract: 'contract_draft',
            quote: 'tkp',
            supporting: 'supporting',
          };
          let lastSearchBaseParams = null;

          function escapeHtml(value) {
            return String(value ?? '')
              .replaceAll('&', '&amp;')
              .replaceAll('<', '&lt;')
              .replaceAll('>', '&gt;')
              .replaceAll('"', '&quot;')
              .replaceAll("'", '&#39;');
          }

          function statusLabel(status) {
            return STATUS_LABELS[status] || status || 'не определено';
          }

          function setFlash(message, isError = false, targetId = 'wizard-flash') {
            const node = document.getElementById(targetId);
            if (!node) return;
            node.textContent = message;
            node.style.display = 'block';
            node.className = isError ? 'flash error' : 'flash';
          }

          function clearFlash(targetId = 'wizard-flash') {
            const node = document.getElementById(targetId);
            if (!node) return;
            node.style.display = 'none';
            node.textContent = '';
            node.className = 'flash';
          }

          function collectFiles(inputId) {
            return Array.from(document.getElementById(inputId).files || []);
          }

          function getTrimmedValue(name) {
            const field = document.querySelector(`[name="${name}"]`);
            return field ? field.value.trim() : '';
          }

          function hasManualFiles() {
            return ['notice-files', 'technical-files', 'contract-files', 'quote-files', 'supporting-files']
              .some((inputId) => collectFiles(inputId).length > 0);
          }

          function appendRoleFiles(formData, files, roleKey) {
            const prefix = fileRolePrefixes[roleKey];
            files.forEach((file, index) => {
              const safeName = `${prefix}_${String(index + 1).padStart(2, '0')}_${file.name}`;
              formData.append('files', file, safeName);
            });
          }

          function buildFilesPayload() {
            const formData = new FormData();
            const noticeFiles = collectFiles('notice-files');
            const technicalFiles = collectFiles('technical-files');
            const contractFiles = collectFiles('contract-files');
            const quoteFiles = collectFiles('quote-files');
            const supportingFiles = collectFiles('supporting-files');

            appendRoleFiles(formData, noticeFiles, 'notice');
            appendRoleFiles(formData, technicalFiles, 'technical');
            appendRoleFiles(formData, contractFiles, 'contract');
            appendRoleFiles(formData, quoteFiles, 'quote');
            appendRoleFiles(formData, supportingFiles, 'supporting');
            return formData;
          }

          function extractReestrNumber(value) {
            const input = String(value || '').trim();
            if (!input) {
              return '';
            }
            const directNumber = input.match(/^(\\d{11,25})$/);
            if (directNumber) {
              return directNumber[1];
            }
            const paramMatch = input.match(/[?&](?:regNumber|reestrNumber|registryNumber)=([0-9]{11,25})/i);
            if (paramMatch) {
              return paramMatch[1];
            }
            const fallbackMatch = input.match(/(\\d{11,25})/);
            return fallbackMatch ? fallbackMatch[1] : '';
          }

          function guessLawFromValue(value) {
            const input = String(value || '').trim().toLowerCase();
            if (!input) {
              return '';
            }
            if (input.includes('/223/')) {
              return '223fz';
            }
            if (input.includes('ea615') || input.includes('capitalrepairs') || input.includes('pprf615') || input.includes('капрем')) {
              return 'capital_repair';
            }
            return '44fz';
          }

          function sourceFromLaw(law) {
            if (law === '223fz') return 'public_eis_html_223fz';
            if (law === 'capital_repair') return 'public_eis_html_capital_repair';
            return 'public_eis_html_44fz';
          }

          function lawLabel(law) {
            if (law === '223fz') return '223-ФЗ';
            if (law === 'capital_repair') return 'Капремонт';
            return '44-ФЗ';
          }

          function relevanceLabel(status) {
            if (status === 'high') return 'Высокая релевантность';
            if (status === 'medium') return 'Средняя релевантность';
            if (status === 'low') return 'Низкая релевантность';
            if (status === 'not_recommended') return 'Нужна ручная проверка';
            return 'Релевантность не определена';
          }

          function buildSearchResultPayload(card = null) {
            const procurementUrl = card?.source_url || getTrimmedValue('procurement_url');
            const reestrNumber = extractReestrNumber(procurementUrl);
            if (!reestrNumber) {
              throw new Error('Не удалось извлечь реестровый номер из ссылки. Вставьте ссылку ЕИС с regNumber или сам номер закупки.');
            }
            const selectedLaw = String(card?.law || guessLawFromValue(procurementUrl) || getTrimmedValue('search_law') || '44fz');
            return {
              source: card?.source || sourceFromLaw(selectedLaw),
              law: selectedLaw,
              reestr_number: reestrNumber,
              source_url: procurementUrl,
              title: card?.title || null,
              customer_name: card?.customer_name || null,
              download_archive: true,
              analyze_after_download: false,
            };
          }

          async function fetchJson(url, options = undefined) {
            const response = await fetch(url, options);
            if (!response.ok) {
              let detail = `HTTP ${response.status}`;
              try {
                const payload = await response.json();
                detail = payload.detail || detail;
              } catch (_error) {
              }
              throw new Error(detail);
            }
            return response.json();
          }

          function formatMoney(value) {
            if (value === null || value === undefined || value === '') {
              return 'не указана';
            }
            const numeric = Number(value);
            if (Number.isNaN(numeric)) {
              return escapeHtml(String(value));
            }
            return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(numeric) + ' руб.';
          }

          function renderSelectedProcurement(card) {
            const node = document.getElementById('selected-procurement');
            if (!card) {
              node.style.display = 'none';
              node.innerHTML = '';
              return;
            }
            node.style.display = 'block';
            node.innerHTML = `
              <strong>Выбрана закупка для прогона</strong>
              <div>${escapeHtml(card.title || card.reestr_number || card.notice_number || 'Закупка')}</div>
              <div class="label-hint" style="margin-top:6px">${escapeHtml(card.notice_number || card.reestr_number || '')} · ${escapeHtml(card.customer_name || 'Заказчик не указан')}</div>
              <div class="search-badges">
                <span class="search-badge">${escapeHtml(card.category || lawLabel(card.law || '44fz'))}</span>
                ${card.procedure_type ? `<span class="search-badge">${escapeHtml(card.procedure_type)}</span>` : ''}
                ${card.status ? `<span class="search-badge">${escapeHtml(card.status)}</span>` : ''}
              </div>
            `;
          }

          function useSearchCard(card) {
            const sourceValue = card.source_url || card.reestr_number || card.notice_number || '';
            document.querySelector('[name="procurement_url"]').value = sourceValue;
            renderSelectedProcurement(card);
            setFlash('Закупка выбрана. При необходимости добавьте файлы и запустите обработку.');
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }

          function searchStatusMessage(payload = {}) {
            const outcome = String(payload.outcome || '');
            const parserStatus = String(payload.parser_status || payload.status || '');
            const error = String(payload.error || '').trim();
            const details = error ? ` Причина: ${escapeHtml(error)}.` : '';
            if (outcome === 'success_with_results') {
              return payload.message || `Поиск завершен. Найдено карточек: ${String((payload.cards || []).length)}.`;
            }
            if (outcome === 'success_empty') {
              return payload.message || 'Источник доступен, но закупки по заданным фильтрам не найдены.';
            }
            if (outcome === 'source_unavailable') {
              if (parserStatus === 'js_heavy') {
                return `ЕИС вернула JS-heavy страницу, поэтому автоматический поиск сейчас недоступен.${details}`;
              }
              return (payload.message || 'Публичный поиск ЕИС сейчас недоступен.') + details;
            }
            if (outcome === 'unsupported_search_mode') {
              return (payload.message || 'Автоматический режим поиска для этого источника не поддерживается.') + details;
            }
            if (outcome === 'validation_error') {
              return (payload.message || 'Проверьте запрос и параметры поиска.') + details;
            }
            return (payload.message || 'Поиск ЕИС завершился с ошибкой.') + details;
          }

          function buildSearchBaseParams() {
            const params = new URLSearchParams();
            params.set('query', getTrimmedValue('search_query'));
            params.set('max_results', String(SEARCH_PAGE_SIZE));
            params.set('page_size', String(SEARCH_PAGE_SIZE));
            params.set('law', getTrimmedValue('search_law') || '44fz');
            const region = getTrimmedValue('search_region');
            const statusFilter = getTrimmedValue('search_status');
            const procedureType = getTrimmedValue('search_procedure_type');
            const dateFrom = getTrimmedValue('search_date_from');
            const dateTo = getTrimmedValue('search_date_to');
            const deadlineFrom = getTrimmedValue('search_deadline_from');
            const deadlineTo = getTrimmedValue('search_deadline_to');
            const priceFrom = getTrimmedValue('search_price_from');
            const priceTo = getTrimmedValue('search_price_to');
            if (region) params.set('region', region);
            if (statusFilter) params.set('status_filter', statusFilter);
            if (procedureType) params.set('procedure_type', procedureType);
            if (dateFrom) params.set('date_from', dateFrom);
            if (dateTo) params.set('date_to', dateTo);
            if (deadlineFrom) params.set('deadline_from', deadlineFrom);
            if (deadlineTo) params.set('deadline_to', deadlineTo);
            if (priceFrom) params.set('price_from', priceFrom);
            if (priceTo) params.set('price_to', priceTo);
            return params;
          }

          function buildSearchPageParams(page) {
            const params = new URLSearchParams(lastSearchBaseParams ? lastSearchBaseParams.toString() : buildSearchBaseParams().toString());
            params.set('page', String(Math.max(1, Number(page) || 1)));
            params.set('page_size', String(SEARCH_PAGE_SIZE));
            params.set('max_results', String(SEARCH_PAGE_SIZE));
            return params;
          }

          function searchResultsMeta(payload = {}, cards = []) {
            const page = Math.max(1, Number(payload.page) || 1);
            const pageSize = Math.max(1, Number(payload.page_size) || SEARCH_PAGE_SIZE);
            const returnedCount = Math.max(0, Number(payload.returned_count) || cards.length);
            const totalCount = Number.isInteger(payload.total_count) ? Number(payload.total_count) : null;
            const startIndex = returnedCount ? ((page - 1) * pageSize) + 1 : 0;
            const endIndex = returnedCount ? startIndex + returnedCount - 1 : 0;
            let countLine = '';
            if (totalCount !== null) {
              countLine = page === 1
                ? `Показаны первые ${String(returnedCount)} карточек из ${String(totalCount)}.`
                : `Показаны карточки ${String(startIndex)}-${String(endIndex)} из ${String(totalCount)}.`;
            } else if (payload.has_more) {
              countLine = page === 1
                ? `Показаны первые ${String(returnedCount)} карточек. Есть ещё результаты.`
                : `Показаны карточки ${String(startIndex)}-${String(endIndex)}. Есть ещё результаты.`;
            } else if (returnedCount) {
              countLine = `Показаны карточки ${String(startIndex)}-${String(endIndex)}.`;
            }
            return { page, pageSize, returnedCount, totalCount, startIndex, endIndex, countLine };
          }

          function renderSearchResults(payload = {}) {
            const cards = payload.cards || [];
            const eisSearchUrl = payload.eis_search_url || '';
            const outcome = String(payload.outcome || '');
            const node = document.getElementById('search-results');
            if (!cards?.length) {
              node.className = 'search-results empty';
              const needsManualLink = eisSearchUrl && outcome !== 'success_empty';
              const emptyHint = outcome === 'success_empty'
                ? 'Ничего не найдено по заданным фильтрам. Попробуйте упростить запрос или изменить диапазоны.'
                : searchStatusMessage(payload);
              node.innerHTML = `
                <div>${emptyHint}</div>
                ${needsManualLink ? `<div style="margin-top:10px"><a class="doc-link" href="${escapeHtml(eisSearchUrl)}" target="_blank" rel="noreferrer">Открыть поиск в ЕИС</a></div>` : ''}
                <div style="margin-top:10px"><button class="button" id="search-results-demo-button" type="button">Открыть демо-закупку 0323100010326000013</button></div>
              `;
              const demoButton = document.getElementById('search-results-demo-button');
              if (demoButton) {
                demoButton.addEventListener('click', useDemoProcurement);
              }
              return;
            }
            node.className = 'search-results';
            const law = cards[0]?.law || getTrimmedValue('search_law') || '44fz';
            const meta = searchResultsMeta(payload, cards);
            const resultWord = cards.length === 1 ? 'карточка' : (cards.length >= 2 && cards.length <= 4 ? 'карточки' : 'карточек');
            node.innerHTML = `
              <div class="search-results-board">
                <div class="search-results-header">
                  <div class="search-results-headline">
                    <div class="search-results-title">Результаты поиска: ${cards.length} ${resultWord} · страница ${String(meta.page)}</div>
                    <div class="search-results-note">${escapeHtml(lawLabel(law))} · сортировка: сначала самые новые · обработка запускается прямо из строки результата</div>
                  </div>
                  <div class="search-results-tools">
                    ${eisSearchUrl ? `<a class="link-button" href="${escapeHtml(eisSearchUrl)}" target="_blank" rel="noreferrer">Открыть поиск в ЕИС</a>` : ''}
                  </div>
                </div>
                <div class="search-list-head">
                  <div>Закупка</div>
                  <div>Ключевые параметры</div>
                  <div>НМЦК и оценка</div>
                  <div>Действие</div>
                </div>
                ${cards.map((card, index) => `
                  <div class="search-card">
                    <div class="search-card-main">
                      ${card.source_url
                        ? `<a class="search-number" href="${escapeHtml(card.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(card.notice_number || card.reestr_number || 'номер не указан')}</a>`
                        : `<div class="search-number">${escapeHtml(card.notice_number || card.reestr_number || 'номер не указан')}</div>`}
                      <h3>${escapeHtml(card.title || 'Закупка без названия')}</h3>
                      <div class="label-hint" style="margin-top:8px">${escapeHtml(card.customer_name || 'Заказчик не указан')}</div>
                      <div class="search-badges">
                        <span class="search-badge">${escapeHtml(card.category || lawLabel(card.law || '44fz'))}</span>
                        ${card.procedure_type ? `<span class="search-badge">${escapeHtml(card.procedure_type)}</span>` : ''}
                        ${card.status ? `<span class="search-badge">${escapeHtml(card.status)}</span>` : ''}
                      </div>
                    </div>
                    <div class="search-card-meta">
                      <div class="search-meta-item"><span class="metric-label">Дата публикации</span><span class="metric-value">${escapeHtml(card.publication_date || 'не указана')}</span></div>
                      <div class="search-meta-item"><span class="metric-label">Срок подачи</span><span class="metric-value">${escapeHtml(card.deadline || 'не указан')}</span></div>
                      <div class="search-meta-item"><span class="metric-label">Заказчик</span><span class="metric-value">${escapeHtml(card.customer_name || 'не указан')}</span></div>
                      <div class="search-meta-item"><span class="metric-label">Номер</span><span class="metric-value">${escapeHtml(card.notice_number || card.reestr_number || 'не указан')}</span></div>
                    </div>
                    <div class="search-price-box">
                      <div>
                        <span class="metric-label">НМЦК</span>
                        <span class="metric-value">${formatMoney(card.initial_price)}</span>
                      </div>
                      <div class="search-relevance ${escapeHtml(card.relevance?.status || 'medium')}">${escapeHtml(relevanceLabel(card.relevance?.status))}${card.relevance?.score !== undefined ? ` · ${escapeHtml(String(Math.round(card.relevance.score)))} / 100` : ''}</div>
                    </div>
                    <div class="search-actions">
                      <button class="button primary search-process-button" type="button" data-index="${index}">Обработать</button>
                      <span class="search-report-slot" data-index="${index}"></span>
                    </div>
                  </div>
                `).join('')}
                <div class="search-results-footer">
                  <div class="search-results-count">${escapeHtml(meta.countLine || '')}</div>
                  <div class="search-results-pagination">
                    ${payload.has_more && payload.next_page ? `<button class="button" id="search-next-page-button" type="button">Показать следующие 10</button>` : ''}
                  </div>
                </div>
              </div>
            `;
            for (const button of node.querySelectorAll('.search-process-button')) {
              button.addEventListener('click', () => processSearchCard(cards[Number(button.dataset.index)], button));
            }
            const nextPageButton = document.getElementById('search-next-page-button');
            if (nextPageButton) {
              nextPageButton.addEventListener('click', () => loadNextSearchPage(payload.next_page));
            }
          }

          async function runSearchPage(page = 1) {
            const params = buildSearchPageParams(page);
            setFlash(page > 1 ? `Загружаем страницу ${String(page)}…` : 'Ищем закупки по ключевым словам и фильтрам…', false, 'search-flash');
            try {
              const payload = await fetchJson(`/api/demo/tender-agent/procurement/public-44fz-search?${params.toString()}`, {
                method: 'POST',
              });
              renderSearchResults(payload);
              setFlash(searchStatusMessage(payload), payload.outcome !== 'success_with_results' && payload.outcome !== 'success_empty', 'search-flash');
            } catch (error) {
              setFlash(`Не удалось выполнить поиск: ${error.message}`, true, 'search-flash');
            }
          }

          async function searchProcurements() {
            clearFlash('search-flash');
            const query = getTrimmedValue('search_query');
            if (!query) {
              setFlash('Введите ключевые слова для поиска закупок.', true, 'search-flash');
              return;
            }
            lastSearchBaseParams = buildSearchBaseParams();
            await runSearchPage(1);
          }

          async function loadNextSearchPage(page) {
            if (!lastSearchBaseParams) {
              setFlash('Сначала выполните поиск с ключевыми словами.', true, 'search-flash');
              return;
            }
            await runSearchPage(page);
          }

          function useDemoProcurement() {
            const demoRegistryNumber = '0323100010326000013';
            document.querySelector('[name="procurement_url"]').value = demoRegistryNumber;
            renderSelectedProcurement({
              reestr_number: demoRegistryNumber,
              notice_number: demoRegistryNumber,
              title: 'Демо-закупка для безопасного показа сценария анализа',
              customer_name: 'Демо-контур Tender Agent',
              law: '44fz',
              category: '44-ФЗ',
              source: 'public_eis_html_44fz',
            });
            setFlash(`Подставлена демо-закупка ${demoRegistryNumber}. Можно сразу запускать обработку или продолжить поиск.`, false, 'search-flash');
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }

          function resetSearchFilters() {
            const fields = [
              'search_law',
              'search_query',
              'search_region',
              'search_status',
              'search_procedure_type',
              'search_date_from',
              'search_date_to',
              'search_deadline_from',
              'search_deadline_to',
              'search_price_from',
              'search_price_to',
            ];
            for (const name of fields) {
              const field = document.querySelector(`[name="${name}"]`);
              if (field) {
                field.value = '';
              }
            }
            const lawField = document.querySelector('[name="search_law"]');
            if (lawField) {
              lawField.value = '44fz';
            }
            clearFlash('search-flash');
            lastSearchBaseParams = null;
            const searchResults = document.getElementById('search-results');
            searchResults.className = 'search-results empty';
            searchResults.innerHTML = 'Введите ключевые слова и при необходимости уточните фильтры. Результаты поиска появятся здесь.';
          }

          function setSearchActionButtonsDisabled(disabled) {
            for (const button of document.querySelectorAll('.search-process-button')) {
              button.disabled = disabled;
            }
          }

          function renderStepTimeline(steps) {
            if (!steps?.length) {
              return '<div class="empty">Пошаговый pipeline пока не сформирован.</div>';
            }
            return `
              <div class="timeline">
                ${steps.map((step) => `
                  <div class="timeline-item">
                    <div class="timeline-title">${escapeHtml(STEP_LABELS[step.key] || step.title || step.key)}</div>
                    <div class="timeline-state">${escapeHtml(statusLabel(step.status))}</div>
                    <div class="timeline-note">${escapeHtml(step.result_summary || step.description || '')}</div>
                  </div>
                `).join('')}
              </div>
            `;
          }

          function renderResult(run) {
            const recommendation = run.final_recommendation || {};
            const quote = run.quote_comparison || {};
            const economics = run.economics_summary || {};
            const reportLink = run.report_html_url
              ? `<a class="link-button primary" href="${escapeHtml(run.report_html_url)}" target="_blank" rel="noreferrer">Открыть HTML-отчёт</a>`
              : '';

            document.getElementById('result-root').innerHTML = `
              <div class="result-shell">
                <div class="metrics">
                  <div class="metric"><span class="metric-label">Run ID</span><span class="metric-value">${escapeHtml(run.run_id)}</span></div>
                  <div class="metric"><span class="metric-label">Статус</span><span class="metric-value">${escapeHtml(statusLabel(run.status))}</span></div>
                  <div class="metric"><span class="metric-label">Файлов</span><span class="metric-value">${escapeHtml(String(run.files?.length || 0))}</span></div>
                  <div class="metric"><span class="metric-label">Режим анализа</span><span class="metric-value">${escapeHtml(run.analysis_mode || 'не определено')}</span></div>
                </div>
                <div class="actions">
                  ${reportLink}
                  <a class="link-button" href="/demo/tender-agent/runs/${encodeURIComponent(run.run_id)}" target="_blank" rel="noreferrer">Открыть полный console view</a>
                </div>
                <div class="result-grid">
                  <div class="result-block">
                    <h3>Рекомендация</h3>
                    <ul>
                      <li><strong>${escapeHtml(recommendation.label || recommendation.recommendation || 'не сформирована')}</strong></li>
                      ${(recommendation.rationale || []).slice(0, 4).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
                    </ul>
                  </div>
                  <div class="result-block">
                    <h3>Что проверить руками</h3>
                    <ul>
                      ${(recommendation.manual_checks || []).slice(0, 5).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
                      ${(run.warnings || []).slice(0, 3).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
                    </ul>
                  </div>
                  <div class="result-block">
                    <h3>ТКП и сравнение</h3>
                    <ul>
                      <li>Найдено предложений поставщиков: ${escapeHtml(String(quote.supplier_quotes_found || 0))}</li>
                      <li>Извлечено сопоставимых позиций: ${escapeHtml(String(quote.items_extracted || 0))}</li>
                      ${((quote.manual_checks || []).slice(0, 3)).map((item) => `<li>${escapeHtml(item.message || item)}</li>`).join('')}
                    </ul>
                  </div>
                  <div class="result-block">
                    <h3>Экономика</h3>
                    <ul>
                      <li>Статус экономики: ${escapeHtml(economics.economics_status || 'не определено')}</li>
                      <li>Выбранная стоимость поставщика: ${escapeHtml(String(economics.supplier_cost_selected ?? 'не определено'))}</li>
                      <li>Предварительная цена подачи: ${escapeHtml(String(economics.preliminary_bid_price ?? 'не определено'))}</li>
                      <li>Оценка кассового разрыва: ${escapeHtml(String(economics.cash_gap_estimate ?? 'не определено'))}</li>
                    </ul>
                  </div>
                </div>
                <div class="result-block">
                  <h3>Шаги обработки</h3>
                  ${renderStepTimeline(run.steps || [])}
                </div>
              </div>
            `;
          }

          async function runProcessing(card = null) {
            clearFlash();
            const button = document.getElementById('process-button');
            button.disabled = true;
            setSearchActionButtonsDisabled(true);
            try {
              if (card) {
                const sourceValue = card.source_url || card.reestr_number || card.notice_number || '';
                document.querySelector('[name="procurement_url"]').value = sourceValue;
                renderSelectedProcurement(card);
              }
              const procurementUrl = getTrimmedValue('procurement_url');
              if (!procurementUrl) {
                throw new Error('Укажите ссылку на закупку, реестровый номер или выберите закупку из результатов поиска.');
              }
              let created;
              let shouldAnalyze = true;
              setFlash('Шаг 1 из 3. Извлекаем номер закупки и запрашиваем документацию ЕИС…');
              created = await fetchJson('/api/demo/tender-agent/runs/from-search-result', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(buildSearchResultPayload(card)),
              });
              if (hasManualFiles()) {
                setFlash(`Шаг 2 из 3. Добавляем ваши файлы в run ${created.run_id}…`);
                await fetchJson(`/api/demo/tender-agent/runs/${encodeURIComponent(created.run_id)}/files`, {
                  method: 'POST',
                  body: buildFilesPayload(),
                });
              }

              if (shouldAnalyze) {
                setFlash(`Шаг 3 из 3. Запускаем анализ для ${created.run_id}…`);
                await fetchJson(`/api/demo/tender-agent/runs/${encodeURIComponent(created.run_id)}/analyze`, {
                  method: 'POST',
                });
              } else {
                setFlash(`Шаг 3 из 3. Автозагрузка документов пока не завершена. Показываю run ${created.run_id} и жду ручного дозаполнения.`, true);
              }

              const run = await fetchJson(`/api/demo/tender-agent/runs/${encodeURIComponent(created.run_id)}`);
              renderResult(run);
              if (shouldAnalyze) {
                setFlash(`Готово. Тендер обработан, статус: ${statusLabel(run.status)}.`);
              }
              return run;
            } catch (error) {
              setFlash(`Обработка не завершена: ${error.message}`, true);
              throw error;
            } finally {
              button.disabled = false;
              setSearchActionButtonsDisabled(false);
            }
          }

          async function processSearchCard(card, button) {
            const originalLabel = button.textContent;
            const actionsNode = button.closest('.search-actions');
            const reportSlot = actionsNode ? actionsNode.querySelector('.search-report-slot') : null;
            button.disabled = true;
            button.textContent = 'Обрабатываем…';
            try {
              const run = await runProcessing(card);
              if (reportSlot && run?.report_html_url) {
                reportSlot.innerHTML = `<a class="link-button" href="${escapeHtml(run.report_html_url)}" target="_blank" rel="noreferrer">Показать отчёт</a>`;
              }
            } finally {
              button.disabled = false;
              button.textContent = originalLabel;
            }
          }

          async function processWizard(event) {
            event.preventDefault();
            await runProcessing();
          }

          function resetWizard() {
            document.getElementById('pilot-form').reset();
            clearFlash();
            clearFlash('search-flash');
            renderSelectedProcurement(null);
            const searchResults = document.getElementById('search-results');
            searchResults.className = 'search-results empty';
            searchResults.textContent = 'Введите ключевые слова и при необходимости уточните фильтры. Результаты поиска появятся здесь.';
          }

          document.getElementById('pilot-form').addEventListener('submit', processWizard);
          document.getElementById('reset-button').addEventListener('click', resetWizard);
          document.getElementById('search-button').addEventListener('click', searchProcurements);
          document.getElementById('search-reset-button').addEventListener('click', resetSearchFilters);
          document.getElementById('search-demo-button').addEventListener('click', useDemoProcurement);
        </script>
      </body>
    </html>
    """
