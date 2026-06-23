from __future__ import annotations

import json


def render_tender_operator_console_html(selected_run_id: str | None = None) -> str:
    initial_run_id = json.dumps(selected_run_id)
    return f"""
    <html lang="ru">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Тендерный агент: демонстрация работы</title>
        <style>
          :root {{
            --mint-primary: #00c8a0;
            --mint-light: #78fae6;
            --deep-navy: #001432;
            --graphite: #283246;
            --soft-gray: #c8d2dc;
            --white: #ffffff;
            --line: rgba(200, 210, 220, 0.16);
            --panel: rgba(255, 255, 255, 0.05);
            --panel-strong: rgba(255, 255, 255, 0.08);
            --warning: #ffb454;
            --danger: #ff7f87;
            --review: #8bd8ff;
          }}
          * {{ box-sizing: border-box; }}
          body {{
            margin: 0;
            font-family: "PT Sans", Arial, sans-serif;
            background:
              radial-gradient(circle at top left, rgba(0, 200, 160, 0.14), transparent 28%),
              linear-gradient(180deg, #03142f 0%, #001432 52%, #071d38 100%);
            color: var(--white);
          }}
          .page {{
            width: min(1440px, calc(100vw - 32px));
            margin: 0 auto;
            padding: 20px 0 48px;
          }}
          .shell {{
            border-radius: 28px;
            border: 1px solid var(--line);
            background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
            overflow: hidden;
            box-shadow: 0 30px 80px rgba(0, 20, 50, 0.28);
          }}
          .header {{
            padding: 28px 28px 20px;
            border-bottom: 1px solid var(--line);
            display: flex;
            justify-content: space-between;
            gap: 24px;
            align-items: flex-start;
          }}
          .brand-lockup {{
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 12px;
          }}
          .brand-lockup img {{
            width: 168px;
            height: auto;
            display: block;
            filter: drop-shadow(0 10px 24px rgba(0, 200, 160, 0.18));
          }}
          .eyebrow {{
            color: var(--mint-light);
            font-size: 12px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 10px;
          }}
          h1 {{
            margin: 0 0 10px;
            font-size: clamp(32px, 4vw, 52px);
            line-height: 0.95;
          }}
          .subtitle {{
            margin: 0;
            max-width: 720px;
            color: rgba(255,255,255,0.78);
            font-size: 18px;
            line-height: 1.45;
          }}
          .badge-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: flex-end;
          }}
          .badge {{
            padding: 10px 14px;
            border-radius: 999px;
            background: rgba(0, 200, 160, 0.13);
            border: 1px solid rgba(120, 250, 230, 0.25);
            color: var(--mint-light);
            font-size: 12px;
            white-space: nowrap;
          }}
          .content {{
            padding: 18px;
            display: grid;
            gap: 18px;
          }}
          .tabs {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
          }}
          .tab-button, .button, .link-button {{
            appearance: none;
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 999px;
            min-height: 44px;
            padding: 0 18px;
            background: rgba(255,255,255,0.05);
            color: var(--white);
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
          }}
          .tab-button.active, .button.primary {{
            background: rgba(0, 200, 160, 0.16);
            border-color: rgba(120, 250, 230, 0.32);
          }}
          .layout {{
            display: grid;
            grid-template-columns: minmax(320px, 0.9fr) minmax(0, 1.35fr);
            gap: 18px;
          }}
          .stack {{
            display: grid;
            gap: 18px;
            align-content: start;
          }}
          .card {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 20px;
          }}
          .card h2, .card h3 {{
            margin: 0 0 14px;
          }}
          .card p {{
            margin: 0;
            color: rgba(255,255,255,0.78);
            line-height: 1.5;
          }}
          .grid-2 {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
          }}
          .metric {{
            padding: 14px;
            border-radius: 16px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.06);
          }}
          .metric-label {{
            display: block;
            color: rgba(255,255,255,0.58);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
          }}
          .metric-value {{
            display: block;
            font-size: 16px;
            line-height: 1.4;
          }}
          .list, .steps-list {{
            list-style: none;
            margin: 0;
            padding: 0;
            display: grid;
            gap: 10px;
          }}
          .list-item {{
            padding: 12px 14px;
            border-radius: 16px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.06);
          }}
          .run-item {{
            padding: 14px;
            border-radius: 18px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.06);
            cursor: pointer;
          }}
          .run-item.active {{
            border-color: rgba(120, 250, 230, 0.3);
            background: rgba(0, 200, 160, 0.11);
          }}
          .run-meta {{
            color: rgba(255,255,255,0.62);
            font-size: 13px;
            margin-top: 4px;
          }}
          .event-list {{
            list-style: none;
            margin: 0;
            padding: 0;
            display: grid;
            gap: 10px;
          }}
          .event-item {{
            padding: 12px 14px;
            border-radius: 14px;
            background: rgba(255,255,255,0.035);
            border: 1px solid rgba(255,255,255,0.06);
          }}
          .event-head {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            color: rgba(255,255,255,0.58);
            font-size: 12px;
            margin-bottom: 6px;
          }}
          .event-severity {{
            color: var(--mint-light);
            text-transform: uppercase;
            letter-spacing: 0.08em;
          }}
          .event-severity.warning {{ color: var(--warning); }}
          .event-severity.error {{ color: var(--danger); }}
          .step-card {{
            padding: 16px;
            border-radius: 18px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.06);
          }}
          .step-top {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
            margin-bottom: 10px;
          }}
          .status-chip {{
            padding: 7px 10px;
            border-radius: 999px;
            background: rgba(255,255,255,0.06);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }}
          .status-done {{ color: var(--mint-light); }}
          .status-partial {{ color: var(--review); }}
          .status-needs_review {{ color: var(--review); }}
          .status-warning {{ color: var(--warning); }}
          .status-blocked {{ color: var(--danger); }}
          .status-pending {{ color: var(--soft-gray); }}
          .status-running {{ color: var(--mint-primary); }}
          .section-title {{
            color: var(--mint-light);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 10px;
          }}
          .split {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
          }}
          .trace {{
            padding: 16px;
            border-radius: 16px;
            background: rgba(0, 200, 160, 0.08);
            border: 1px solid rgba(120, 250, 230, 0.18);
            color: rgba(255,255,255,0.88);
            font-size: 14px;
            line-height: 1.6;
          }}
          .safety {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
          }}
          .safety span {{
            padding: 10px 12px;
            border-radius: 999px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            color: rgba(255,255,255,0.78);
            font-size: 13px;
          }}
          form {{
            display: grid;
            gap: 12px;
          }}
          label {{
            display: grid;
            gap: 8px;
            font-size: 14px;
            color: rgba(255,255,255,0.86);
          }}
          .checkbox {{
            display: flex;
            align-items: center;
            gap: 10px;
          }}
          .checkbox input {{
            width: 18px;
            min-height: 18px;
            height: 18px;
            margin: 0;
            padding: 0;
          }}
          .checkbox span {{
            color: rgba(255,255,255,0.86);
          }}
          input, select, textarea {{
            width: 100%;
            min-height: 46px;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.05);
            color: var(--white);
            padding: 0 14px;
            font: inherit;
          }}
          textarea {{
            min-height: 96px;
            padding-top: 12px;
            resize: vertical;
          }}
          input[type="file"] {{
            padding: 10px 14px;
          }}
          .form-actions {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
          }}
          .note {{
            font-size: 13px;
            color: rgba(255,255,255,0.62);
            line-height: 1.5;
          }}
          table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
          }}
          th, td {{
            text-align: left;
            padding: 9px 8px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            vertical-align: top;
          }}
          th {{
            color: var(--mint-light);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }}
          .flash {{
            padding: 12px 14px;
            border-radius: 14px;
            border: 1px solid rgba(120,250,230,0.22);
            background: rgba(0,200,160,0.12);
            color: rgba(255,255,255,0.9);
          }}
          .flash.error {{
            background: rgba(255, 127, 135, 0.12);
            border-color: rgba(255, 127, 135, 0.28);
          }}
          .hidden {{
            display: none !important;
          }}
          .empty {{
            padding: 28px 16px;
            border-radius: 18px;
            border: 1px dashed rgba(255,255,255,0.16);
            color: rgba(255,255,255,0.66);
            text-align: center;
          }}
          a.inline-link {{
            color: var(--mint-light);
          }}
          @media (max-width: 1080px) {{
            .layout, .split {{
              grid-template-columns: 1fr;
            }}
          }}
          @media (max-width: 700px) {{
            .page {{
              width: min(100vw - 20px, 1440px);
              padding-top: 10px;
            }}
            .header {{
              flex-direction: column;
              padding: 22px 18px 18px;
            }}
            .content {{
              padding: 14px;
            }}
            .grid-2 {{
              grid-template-columns: 1fr;
            }}
          }}
        </style>
      </head>
      <body>
        <div class="page">
          <div class="shell">
            <header class="header">
              <div>
                <div class="brand-lockup">
                  <img src="/demo/tender-agent/assets/arvectum-logo-block.svg" alt="Arvectum" />
                  <div class="eyebrow">Демонстрация тендерного агента</div>
                </div>
                <h1>Тендерный агент</h1>
                <p class="subtitle">Как ИИ-агент разбирает закупку, готовит RFQ, показывает риски и оставляет критичные действия под контролем человека.</p>
              </div>
              <div class="badge-row">
                <span class="badge">Демо-режим / подтверждение человеком</span>
                <span class="badge">Пилотный контур</span>
                <span class="badge">Без внешних действий</span>
              </div>
            </header>

            <div class="content">
              <div class="tabs">
                <button class="tab-button active" data-tab="search" type="button">Найти закупку</button>
                <button class="tab-button" data-tab="docs" type="button">Получить документацию по номеру</button>
                <button class="tab-button" data-tab="upload" type="button">Загрузить документы</button>
                <button class="tab-button" data-tab="dataset" type="button">Демо-набор</button>
              </div>

              <section id="tab-search">
                <div class="layout">
                  <aside class="stack">
                    <div class="card">
                      <h2>Найти закупку</h2>
                      <p>Первый шаг controlled demo-сценария: найти закупку, выбрать карточку, безопасно получить публичную документацию или честно перейти к ручной загрузке.</p>
                      <div id="procurement-flash" class="hidden"></div>
                      <form id="procurement-search-form">
                        <label>
                          Поисковый запрос
                          <input name="query" value="электротехническое оборудование" />
                        </label>
                        <div class="split">
                          <label>
                            Источник
                            <select name="source" id="procurement-source-select">
                              <option value="demo_local">demo_local</option>
                              <option value="public_eis_html_44fz">public_eis_html_44fz</option>
                              <option value="public_eis_html_223fz">public_eis_html_223fz</option>
                            </select>
                          </label>
                          <label>
                            Макс. результатов
                            <input name="max_results" type="number" min="1" max="20" value="10" />
                          </label>
                        </div>
                        <div class="split">
                          <label>
                            Закон
                            <select name="law">
                              <option value="">Все</option>
                              <option value="44-ФЗ">44-ФЗ</option>
                              <option value="223-ФЗ">223-ФЗ</option>
                            </select>
                          </label>
                          <label>
                            ИНН заказчика
                            <input name="customer_inn" placeholder="Необязательно" />
                          </label>
                        </div>
                        <div class="split">
                          <label>
                            Заказчик
                            <input name="customer_name" placeholder="Необязательно" />
                          </label>
                          <label>
                            Регион
                            <input name="region" placeholder="Необязательно" />
                          </label>
                        </div>
                        <div class="split">
                          <label>
                            Дата публикации с
                            <input name="date_from" type="date" />
                          </label>
                          <label>
                            Дата публикации по
                            <input name="date_to" type="date" />
                          </label>
                        </div>
                        <div class="split">
                          <label>
                            Цена от
                            <input name="price_from" type="number" min="0" step="1000" placeholder="Необязательно" />
                          </label>
                          <label>
                            Цена до
                            <input name="price_to" type="number" min="0" step="1000" placeholder="Необязательно" />
                          </label>
                        </div>
                        <div class="form-actions">
                          <button class="button primary" type="submit">Найти закупки</button>
                        </div>
                      </form>
                    </div>
                    <div class="card">
                      <h2>Диагностика ЕИС</h2>
                      <div id="procurement-source-diagnostics" class="list">
                        <div class="empty">Диагностика источника загрузится автоматически.</div>
                      </div>
                    </div>
                    <div class="card">
                      <h2>Безопасный режим</h2>
                      <div class="safety">
                        <span>Read-only поиск</span>
                        <span>Без логина и паролей</span>
                        <span>Без обхода captcha</span>
                        <span>Без подачи на площадку</span>
                        <span>Без писем поставщикам</span>
                        <span>Требуется подтверждение человека</span>
                      </div>
                      <p style="margin-top:14px">Поиск работает в безопасном read-only режиме. Система не подаёт заявки, не входит на площадки под учётной записью, не обходит captcha, не использует ЭЦП и не отправляет письма поставщикам.</p>
                    </div>
                  </aside>

                  <main class="stack">
                    <div class="card" id="procurement-results-card">
                      <h2>Результаты поиска</h2>
                      <div id="procurement-results" class="list">
                        <div class="empty">Введите запрос и нажмите «Найти закупки», чтобы открыть первый шаг тендерного pipeline.</div>
                      </div>
                    </div>
                    <div class="card">
                      <h2>Как это работает</h2>
                      <p>Поиск закупки и получение документации разделены. Сначала вы находите закупку через offline-safe `demo_local` или публичный HTML fallback, затем либо переходите к ручной загрузке, либо используете отдельный getDocsIP intake по реестровому номеру.</p>
                      <div class="trace" style="margin-top:14px">Если автоматическое получение документации недоступно, интерфейс не притворяется автономным: создаётся run со статусом «нужна загрузка документов», а оператор вручную добавляет пакет и только потом запускает анализ.</div>
                    </div>
                  </main>
                </div>
              </section>

              <section id="tab-docs" class="hidden">
                <div class="layout">
                  <aside class="stack">
                    <div class="card">
                      <h2>Получить документацию по номеру</h2>
                      <p>Токен выпущен как физическое лицо. Используется сервис getDocsIP для read-only получения публичной документации по номеру закупки.</p>
                      <div id="eis-docs-flash" class="hidden"></div>
                      <form id="eis-docs-form">
                        <label>
                          Реестровый номер / номер извещения
                          <input name="reestr_number" required placeholder="Например: 0888200000224000038" />
                        </label>
                        <div class="split">
                          <label>
                            Закон
                            <select name="law">
                              <option value="44fz">44-ФЗ</option>
                            </select>
                          </label>
                          <label>
                            Подсистема
                            <input name="subsystem_type" value="PRIZ" />
                          </label>
                        </div>
                        <label>
                          SOAP method
                          <input name="method" value="getDocsByReestrNumber" readonly />
                        </label>
                        <label class="checkbox">
                          <input name="download_archive" type="checkbox" checked />
                          <span>Скачать архив</span>
                        </label>
                        <label class="checkbox">
                          <input name="analyze_after_download" type="checkbox" />
                          <span>Запустить анализ после скачивания</span>
                        </label>
                        <div class="form-actions">
                          <button class="button primary" type="submit">Получить документацию из ЕИС</button>
                        </div>
                      </form>
                    </div>
                    <div class="card">
                      <h2>Диагностика getDocsIP</h2>
                      <div id="eis-docs-diagnostics" class="list">
                        <div class="empty">Диагностика getDocsIP загрузится автоматически.</div>
                      </div>
                    </div>
                    <div class="card">
                      <h2>Ограничения</h2>
                      <div class="safety">
                        <span>Токен физлица</span>
                        <span>Read-only getDocsIP</span>
                        <span>Без личного кабинета</span>
                        <span>Без ЭЦП</span>
                        <span>Без подачи заявки</span>
                        <span>Без писем поставщикам</span>
                      </div>
                      <p style="margin-top:14px">Токен выпущен как физическое лицо. Используется сервис getDocsIP для read-only получения публичной документации по номеру закупки. Система не входит в личный кабинет, не подаёт заявки, не использует ЭЦП и не отправляет письма.</p>
                    </div>
                  </aside>
                  <main class="stack">
                    <div class="card">
                      <h2>Сценарий работы</h2>
                      <div class="trace">1. Найдите закупку через `demo_local` или публичный HTML fallback. 2. Скопируйте реестровый номер. 3. Запросите архив документации через getDocsIP. 4. Если archiveUrl получен, архив скачивается и safely обрабатывается локально. 5. Если archiveUrl не получен, интерфейс честно переводит вас в ручной upload fallback.</div>
                    </div>
                    <div class="card" id="eis-docs-result-card">
                      <h2>Результат получения документации</h2>
                      <div id="eis-docs-result" class="empty">После запроса сюда попадут статус SOAP, статус архива, количество распакованных файлов и ссылки на run/report.</div>
                    </div>
                  </main>
                </div>
              </section>

              <section id="tab-upload" class="hidden">
                <div class="layout">
                  <aside class="stack">
                    <div class="card">
                      <h2>Загрузка и анализ</h2>
                      <p>Локальная загрузка документов закупки, безопасное сохранение в рабочую директорию и контролируемый pipeline анализа без внешних интеграций.</p>
                      <div id="upload-flash" class="hidden"></div>
                      <form id="upload-form">
                        <label>
                          Название закупки
                          <input name="tender_title" required value="Поставка электротехнического оборудования" />
                        </label>
                        <label>
                          Категория
                          <select name="tender_category">
                            <option>Электротехническое оборудование</option>
                            <option>Кабельная продукция</option>
                            <option>Шкафы управления</option>
                            <option>Промышленная автоматизация</option>
                          </select>
                        </label>
                        <label>
                          Заказчик
                          <input name="customer_name" value="Промышленный заказчик" />
                        </label>
                        <label>
                          Комментарий оператора
                          <textarea name="notes" placeholder="Например: демонстрационный прогон для встречи с заказчиком, без ТКП"></textarea>
                        </label>
                        <div class="split">
                          <label>
                            Целевая маржа, %
                            <input name="target_margin_percent" type="number" step="0.1" min="0" max="95" value="15" />
                          </label>
                          <label>
                            Резерв логистики, %
                            <input name="logistics_reserve_percent" type="number" step="0.1" min="0" max="95" value="3" />
                          </label>
                        </div>
                        <div class="split">
                          <label>
                            Резерв риска, %
                            <input name="risk_reserve_percent" type="number" step="0.1" min="0" max="95" value="5" />
                          </label>
                          <label>
                            Отсрочка оплаты, дней
                            <input name="payment_delay_days" type="number" step="1" min="0" max="365" value="45" />
                          </label>
                        </div>
                        <label>
                          Файлы закупки
                          <input name="files" type="file" multiple required />
                        </label>
                        <div class="note">Поддержаны: PDF, DOCX, XLSX, XLS, TXT, CSV, ZIP. В демо-режиме действуют безопасные лимиты на размер и количество файлов.</div>
                        <div class="form-actions">
                          <button class="button primary" type="submit">Создать демонстрационный прогон</button>
                        </div>
                      </form>
                    </div>

                    <div class="card">
                      <h2>Последние прогоны</h2>
                      <div id="runs-list" class="list">
                        <div class="empty">Пока нет загруженных прогонов.</div>
                      </div>
                    </div>
                  </aside>

                  <main class="stack">
                    <div class="card" id="selected-run-card">
                      <div class="empty">Создайте демонстрационный прогон или выберите существующий справа, чтобы увидеть детали анализа.</div>
                    </div>
                    <div class="card" id="selected-run-steps">
                      <div class="empty">Pipeline загруженного прогона появится после запуска анализа.</div>
                    </div>
                    <div class="card" id="selected-run-summary">
                      <div class="empty">Финальная рекомендация для загруженного прогона появится здесь.</div>
                    </div>
                  </main>
                </div>
              </section>

              <section id="tab-dataset" class="hidden">
                <div class="layout">
                  <aside class="stack">
                    <div class="card" id="dataset-tender-card">
                      <div class="empty">Загрузка демонстрационного набора…</div>
                    </div>
                    <div class="card">
                      <h2>Ограничения демо</h2>
                      <div class="safety">
                        <span>Только синтетические demo-data</span>
                        <span>Без подачи на площадку</span>
                        <span>Без отправки писем</span>
                        <span>Без ЭЦП</span>
                        <span>Требуется подтверждение человека</span>
                      </div>
                    </div>
                  </aside>

                  <main class="stack">
                    <div class="card">
                      <div class="step-top">
                        <div>
                          <h2>Pipeline агента</h2>
                          <p>Документы → Требования → Вопросы → RFQ → ТКП → Экономика → Риски → Решение</p>
                        </div>
                        <button class="button primary" id="replay-dataset" type="button">Запустить демонстрационный прогон</button>
                      </div>
                      <div class="steps-list" id="dataset-steps"></div>
                    </div>
                    <div class="card" id="dataset-summary">
                      <div class="empty">Собираем финальную рекомендацию…</div>
                    </div>
                  </main>
                </div>
              </section>
            </div>
          </div>
        </div>

        <script>
          const state = {{
            procurementSources: [],
            procurementResults: [],
            datasetRun: null,
            datasetReplayActive: false,
            datasetDisplayStatuses: new Map(),
            uploadedRuns: [],
            selectedRunId: {initial_run_id},
          }};

          const STEP_STATUS_LABELS = {{
            pending: 'ожидает',
            running: 'в работе',
            done: 'выполнено',
            partial: 'частично',
            needs_review: 'нужна проверка',
            warning: 'риск',
            blocked: 'заблокировано',
          }};

          const RUN_STATUS_LABELS = {{
            uploaded: 'загружено',
            docs_required: 'нужна загрузка документов',
            ready_to_analyze: 'готово к анализу',
            analyzing: 'анализируется',
            completed: 'завершено',
            completed_with_warnings: 'завершено с ограничениями',
            failed: 'ошибка',
            needs_review: 'нужна проверка',
          }};

          const ANALYSIS_MODE_LABELS = {{
            not_started: 'не запущен',
            analyzing: 'анализ выполняется',
            controlled_runner_adapter: 'контролируемый адаптер раннера',
            fallback_deterministic_adapter: 'детерминированный fallback-адаптер',
          }};

          const ATTACHMENTS_STATUS_LABELS = {{
            downloadable: 'можно скачать',
            downloaded: 'документация получена',
            manual_upload_required: 'нужна ручная загрузка',
            manual_upload_received: 'документы загружены вручную',
            unavailable_in_demo: 'недоступно в демо-режиме',
            source_requires_authorization: 'источник требует авторизации или интерактивного доступа',
          }};

          const statusClass = (status) => `status-${{status || 'pending'}}`;

          function statusLabel(status) {{
            return STEP_STATUS_LABELS[status] || RUN_STATUS_LABELS[status] || status || 'ожидает';
          }}

          function analysisModeLabel(mode) {{
            return ANALYSIS_MODE_LABELS[mode] || mode || 'не определено';
          }}

          function attachmentsStatusLabel(status) {{
            return ATTACHMENTS_STATUS_LABELS[status] || status || 'не определено';
          }}

          function booleanLabel(value) {{
            return value ? 'да' : 'нет';
          }}

          function displayValue(value, fallback = 'не определено') {{
            if (value === null || value === undefined || value === '') {{
              return fallback;
            }}
            if (value === true) {{
              return 'да';
            }}
            if (value === false) {{
              return 'нет';
            }}
            if (value === 'unknown') {{
              return fallback;
            }}
            return String(value);
          }}

          function escapeHtml(value) {{
            return String(value ?? '')
              .replaceAll('&', '&amp;')
              .replaceAll('<', '&lt;')
              .replaceAll('>', '&gt;')
              .replaceAll('"', '&quot;')
              .replaceAll("'", '&#39;');
          }}

          function formatMoney(value, currency = '') {{
            if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) {{
              return 'не определено';
            }}
            const number = Number(value);
            const suffix = currency ? ` ${{currency}}` : '';
            return `${{number.toLocaleString('ru-RU', {{ maximumFractionDigits: 2 }})}}${{suffix}}`;
          }}

          function renderQuoteSection(run) {{
            const comparison = run.quote_comparison;
            if (!comparison) {{
              return `<div class="empty">Нормализованные ТКП появятся после завершения анализа.</div>`;
            }}
            const suppliers = comparison.suppliers || [];
            const items = comparison.items || [];
            const manualChecks = [
              ...(comparison.manual_checks || []).map((item) => item.message),
              ...(comparison.limitations || []),
            ];
            return `
              <div class="card" style="padding:16px">
                <div class="section-title">Извлечённые ТКП</div>
                ${{
                  suppliers.length
                    ? `<div class="grid-2">${{suppliers.map((supplier) => `
                      <div class="metric">
                        <span class="metric-label">${{escapeHtml(supplier.supplier_name)}}</span>
                        <span class="metric-value">${{formatMoney(supplier.total_amount, supplier.currency || '')}}</span>
                        <div class="run-meta">${{escapeHtml(supplier.source_file)}} · позиций=${{supplier.items_count}} · уверенность=${{supplier.price_confidence}}</div>
                      </div>
                    `).join('')}}</div>`
                    : `<div class="empty">ТКП не распознаны как структурированные таблицы.</div>`
                }}
              </div>
              <div class="card" style="padding:16px">
                <div class="section-title">Сравнение предложений</div>
                ${{
                  items.length
                    ? `<div style="overflow:auto"><table>
                        <thead><tr><th>Позиция</th><th>Лучшая цена</th><th>Разброс %</th><th>Проверка</th></tr></thead>
                        <tbody>${{items.slice(0, 18).map((item) => `
                          <tr>
                            <td>${{escapeHtml(item.normalized_name)}}</td>
                            <td>${{escapeHtml(displayValue(item.best_price_supplier))}}</td>
                            <td>${{escapeHtml(displayValue(item.price_spread_percent))}}</td>
                            <td>${{item.needs_review ? 'нужна проверка' : 'без замечаний'}}</td>
                          </tr>
                        `).join('')}}</tbody>
                      </table></div>`
                    : `<div class="empty">Сравнение позиций пока недоступно.</div>`
                }}
              </div>
              <div class="card" style="padding:16px">
                <div class="section-title">Что проверить вручную</div>
                <ul>${{manualChecks.length ? manualChecks.map((item) => `<li>${{escapeHtml(item)}}</li>`).join('') : '<li>Дополнительных замечаний нет.</li>'}}</ul>
              </div>
            `;
          }}

          function renderEconomicsSection(run) {{
            const economics = run.economics_summary;
            if (!economics) {{
              return `<div class="empty">Экономика появится после завершения анализа.</div>`;
            }}
            const manualChecks = [
              ...(economics.manual_checks || []).map((item) => item.message),
              ...(economics.limitations || []),
            ];
            return `
              <div class="card" style="padding:16px">
                <div class="section-title">Экономика</div>
                <div class="grid-2">
                  <div class="metric"><span class="metric-label">Минимальная закупочная стоимость</span><span class="metric-value">${{formatMoney(economics.supplier_cost_min, economics.currency || '')}}</span></div>
                  <div class="metric"><span class="metric-label">Выбранная закупочная стоимость</span><span class="metric-value">${{formatMoney(economics.supplier_cost_selected, economics.currency || '')}}</span></div>
                  <div class="metric"><span class="metric-label">Резерв логистики</span><span class="metric-value">${{formatMoney(economics.logistics_reserve, economics.currency || '')}}</span></div>
                  <div class="metric"><span class="metric-label">Резерв риска</span><span class="metric-value">${{formatMoney(economics.risk_reserve, economics.currency || '')}}</span></div>
                  <div class="metric"><span class="metric-label">Целевая маржа</span><span class="metric-value">${{economics.gross_margin_percent === null || economics.gross_margin_percent === undefined ? 'не определено' : `${{escapeHtml(economics.gross_margin_percent)}}%`}}</span></div>
                  <div class="metric"><span class="metric-label">Предварительная цена подачи</span><span class="metric-value">${{formatMoney(economics.preliminary_bid_price, economics.currency || '')}}</span></div>
                </div>
                <div class="trace" style="margin-top:12px">Статус экономики: ${{escapeHtml(displayValue(economics.economics_status))}}. Выбранный поставщик: ${{escapeHtml(displayValue(economics.selected_supplier_name))}}.</div>
              </div>
              <div class="card" style="padding:16px">
                <div class="section-title">Что проверить вручную</div>
                <ul>${{manualChecks.length ? manualChecks.map((item) => `<li>${{escapeHtml(item)}}</li>`).join('') : '<li>Дополнительных замечаний нет.</li>'}}</ul>
              </div>
            `;
          }}

          async function fetchJson(url, options) {{
            const response = await fetch(url, options);
            if (!response.ok) {{
              let detail = `HTTP ${{response.status}}`;
              try {{
                const payload = await response.json();
                detail = payload.detail || detail;
              }} catch (_error) {{
              }}
              throw new Error(detail);
            }}
            return response.json();
          }}

          function setFlash(nodeId, message, isError = false) {{
            const node = document.getElementById(nodeId);
            node.className = `flash${{isError ? ' error' : ''}}`;
            node.textContent = message;
            node.classList.remove('hidden');
          }}

          function clearFlash(nodeId) {{
            const node = document.getElementById(nodeId);
            node.className = 'hidden';
            node.textContent = '';
          }}

          function wireTabs() {{
            for (const button of document.querySelectorAll('.tab-button')) {{
              button.addEventListener('click', () => {{
                for (const item of document.querySelectorAll('.tab-button')) {{
                  item.classList.toggle('active', item === button);
                }}
                const target = button.dataset.tab;
                document.getElementById('tab-search').classList.toggle('hidden', target !== 'search');
                document.getElementById('tab-docs').classList.toggle('hidden', target !== 'docs');
                document.getElementById('tab-dataset').classList.toggle('hidden', target !== 'dataset');
                document.getElementById('tab-upload').classList.toggle('hidden', target !== 'upload');
              }});
            }}
          }}

          function procurementActionLabel(result) {{
            if (result.can_download_attachments || result.attachments_status === 'downloadable') {{
              return 'Скачать документацию и анализировать';
            }}
            return 'Создать run и загрузить документы вручную';
          }}

          async function loadProcurementSources() {{
            state.procurementSources = await fetchJson('/api/demo/tender-agent/procurement/sources');
            const select = document.getElementById('procurement-source-select');
            select.innerHTML = state.procurementSources.filter((source) => ['demo_local', 'public_eis_html_44fz', 'public_eis_html_223fz'].includes(source.source)).map((source) => `
              <option value="${{escapeHtml(source.source)}}"${{source.configured ? '' : ' disabled'}}>${{escapeHtml(source.label)}}${{source.configured ? '' : ` — ${{escapeHtml(source.reason || 'не настроен')}}`}}</option>
            `).join('');
            if (!state.procurementSources.some((source) => source.source === select.value && source.configured)) {{
              select.value = 'demo_local';
            }}
            renderProcurementSourceDiagnostics(select.value);
            renderEisDocsDiagnostics();
            select.addEventListener('change', () => renderProcurementSourceDiagnostics(select.value));
          }}

          function renderProcurementSourceDiagnostics(selectedSource) {{
            const node = document.getElementById('procurement-source-diagnostics');
            const source = state.procurementSources.find((item) => item.source === selectedSource) || state.procurementSources[0];
            if (!source) {{
              node.innerHTML = `<div class="empty">Источник ещё не загружен.</div>`;
              return;
            }}
            const diagnostics = source.safe_diagnostics || {{}};
            const lastStatus = diagnostics.last_status || (source.configured ? 'configured' : 'not_configured');
            const tokenState = diagnostics.token_present ? 'токен найден' : 'токен не найден';
            const statusLabel = source.configured ? 'ЕИС настроена: токен найден' : (source.reason || 'ЕИС не настроена');
            node.innerHTML = `
              <div class="list-item">
                <strong>${{escapeHtml(source.label)}}</strong>
                <div class="run-meta">${{escapeHtml(statusLabel)}}</div>
              </div>
              <div class="list-item">
                <strong>Статус подключения</strong>
                <div class="run-meta">configured=${{source.configured ? 'true' : 'false'}} · ${{escapeHtml(tokenState)}} · last_status=${{escapeHtml(String(lastStatus))}}</div>
              </div>
              <div class="list-item">
                <strong>Endpoint</strong>
                <div class="run-meta">${{escapeHtml(displayValue(diagnostics.endpoint_host, 'не определён'))}}${{escapeHtml(displayValue(diagnostics.endpoint_path, ''))}}</div>
              </div>
              <div class="list-item">
                <strong>Последняя диагностика</strong>
                <div class="run-meta">${{escapeHtml(displayValue(diagnostics.last_error || source.reason, 'ошибок не зафиксировано'))}}</div>
              </div>
            `;
          }}

          function renderEisDocsDiagnostics() {{
            const node = document.getElementById('eis-docs-diagnostics');
            const source = state.procurementSources.find((item) => item.source === 'zakupki_gov_ru_getdocs_ip');
            if (!source) {{
              node.innerHTML = `<div class="empty">Источник getDocsIP ещё не загружен.</div>`;
              return;
            }}
            const diagnostics = source.safe_diagnostics || {{}};
            node.innerHTML = `
              <div class="list-item">
                <strong>${{escapeHtml(source.label)}}</strong>
                <div class="run-meta">${{escapeHtml(source.reason || 'Источник загружен')}}</div>
              </div>
              <div class="list-item">
                <strong>Статус</strong>
                <div class="run-meta">configured=${{source.configured ? 'true' : 'false'}} · token_owner=${{escapeHtml(displayValue(diagnostics.token_owner, 'unknown'))}} · token_present=${{diagnostics.token_present ? 'true' : 'false'}}</div>
              </div>
              <div class="list-item">
                <strong>Endpoint getDocsIP</strong>
                <div class="run-meta">${{escapeHtml(displayValue(diagnostics.endpoint_host, 'не определён'))}}${{escapeHtml(displayValue(diagnostics.endpoint_path, ''))}}</div>
              </div>
              <div class="list-item">
                <strong>Последняя диагностика</strong>
                <div class="run-meta">${{escapeHtml(displayValue(diagnostics.last_error || diagnostics.method_name || source.reason, 'ошибок не зафиксировано'))}}</div>
              </div>
            `;
          }}

          function renderProcurementResults() {{
            const node = document.getElementById('procurement-results');
            if (!state.procurementResults.length) {{
              node.innerHTML = `<div class="empty">По текущему фильтру закупки не найдены. Уточните запрос или используйте demo_local без дополнительных фильтров.</div>`;
              return;
            }}
            node.innerHTML = state.procurementResults.map((result) => `
              <div class="run-item">
                <div class="step-top" style="margin-bottom:8px">
                  <div>
                    <strong>${{escapeHtml(result.title)}}</strong>
                    <div class="run-meta">${{escapeHtml(result.notice_number || result.procurement_number || result.procurement_id)}} · ${{escapeHtml(result.customer_name)}} · ${{escapeHtml(result.law || result.source)}}</div>
                  </div>
                  <span class="status-chip ${{result.attachments_status === 'downloadable' ? 'status-done' : 'status-needs_review'}}">${{escapeHtml(attachmentsStatusLabel(result.attachments_status))}}</span>
                </div>
                <div class="grid-2">
                  <div class="metric"><span class="metric-label">Дата публикации</span><span class="metric-value">${{escapeHtml(displayValue(result.publication_date))}}</span></div>
                  <div class="metric"><span class="metric-label">Срок подачи</span><span class="metric-value">${{escapeHtml(displayValue(result.deadline))}}</span></div>
                  <div class="metric"><span class="metric-label">Начальная цена</span><span class="metric-value">${{formatMoney(result.initial_price, result.currency || '')}}</span></div>
                  <div class="metric"><span class="metric-label">Регион</span><span class="metric-value">${{escapeHtml(displayValue(result.region))}}</span></div>
                </div>
                <div style="height:12px"></div>
                <p>${{escapeHtml(result.summary || result.status || '')}}</p>
                <div class="note" style="margin-top:10px">${{escapeHtml((result.warnings || []).join(' '))}}</div>
                <div class="note" style="margin-top:8px">Вложений: ${{result.attachments_count}} · статус: ${{attachmentsStatusLabel(result.attachments_status)}}</div>
                <div class="form-actions" style="margin-top:12px">
                  <a class="link-button" href="${{result.source_url}}" target="_blank" rel="noreferrer">Открыть источник</a>
                  <button class="button primary procurement-run-button" type="button" data-procurement-id="${{escapeHtml(result.procurement_id)}}" data-source="${{escapeHtml(result.source)}}" data-auto-analyze="${{result.can_download_attachments || result.attachments_status === 'downloadable' ? 'true' : 'false'}}">${{procurementActionLabel(result)}}</button>
                </div>
              </div>
            `).join('');

            for (const button of node.querySelectorAll('.procurement-run-button')) {{
              button.addEventListener('click', () => {{
                createProcurementRun(button.dataset.procurementId, button.dataset.source, button.dataset.autoAnalyze === 'true');
              }});
            }}
          }}

          function renderEisDocsResult(result) {{
            const node = document.getElementById('eis-docs-result');
            if (!result) {{
              node.innerHTML = 'После запроса сюда попадут статус SOAP, статус архива, количество распакованных файлов и ссылки на run/report.';
              node.className = 'empty';
              return;
            }}
            node.className = '';
            const analyzeButton = result.status !== 'docs_required'
              ? `<button class="button primary" type="button" id="eis-result-analyze-button">Запустить анализ</button>`
              : '';
            const reportLink = result.report_url
              ? `<a class="link-button" href="${{escapeHtml(result.report_url)}}" target="_blank" rel="noreferrer">Открыть report</a>`
              : '';
            node.innerHTML = `
              <div class="grid-2">
                <div class="metric"><span class="metric-label">Run ID</span><span class="metric-value">${{escapeHtml(result.run_id)}}</span></div>
                <div class="metric"><span class="metric-label">Статус run</span><span class="metric-value">${{escapeHtml(statusLabel(result.status))}}</span></div>
                <div class="metric"><span class="metric-label">SOAP method</span><span class="metric-value">${{escapeHtml(displayValue(result.soap_method))}}</span></div>
                <div class="metric"><span class="metric-label">refId</span><span class="metric-value">${{escapeHtml(displayValue(result.ref_id))}}</span></div>
                <div class="metric"><span class="metric-label">archiveUrl</span><span class="metric-value">${{booleanLabel(result.archive_url_present)}}</span></div>
                <div class="metric"><span class="metric-label">Статус скачивания</span><span class="metric-value">${{escapeHtml(displayValue(result.archive_download_status))}}</span></div>
                <div class="metric"><span class="metric-label">Архив скачан</span><span class="metric-value">${{booleanLabel(result.archive_downloaded)}}</span></div>
                <div class="metric"><span class="metric-label">Распаковано документов</span><span class="metric-value">${{escapeHtml(displayValue(result.documents_extracted_count, '0'))}}</span></div>
                <div class="metric"><span class="metric-label">Источник архива</span><span class="metric-value">${{escapeHtml(displayValue(result.archive_source_host && result.archive_source_path ? `${{result.archive_source_host}}${{result.archive_source_path}}` : null))}}</span></div>
                <div class="metric"><span class="metric-label">Analysis status</span><span class="metric-value">${{escapeHtml(displayValue(result.analysis_status, 'not_started'))}}</span></div>
              </div>
              <div class="form-actions" style="margin-top:14px">
                <a class="link-button" href="${{escapeHtml(result.run_url)}}" target="_blank" rel="noreferrer">Открыть run</a>
                ${{reportLink}}
                ${{analyzeButton}}
              </div>
              <div class="note" style="margin-top:12px">Полный archive URL и ticket в интерфейсе не показываются. Отображаются только host/path summary.</div>
            `;
            const analyzeButtonNode = document.getElementById('eis-result-analyze-button');
            if (analyzeButtonNode) {{
              analyzeButtonNode.addEventListener('click', async () => {{
                await analyzeRun(result.run_id);
                await selectRun(result.run_id, true);
              }});
            }}
          }}

          async function handleProcurementSearch(event) {{
            event.preventDefault();
            clearFlash('procurement-flash');
            const form = event.currentTarget;
            const payload = {{}};
            for (const [key, value] of new FormData(form).entries()) {{
              if (String(value).trim() !== '') {{
                payload[key] = ['max_results', 'price_from', 'price_to'].includes(key) ? Number(value) : String(value);
              }}
            }}
            try {{
              if (String(payload.source || '').startsWith('public_eis_html_')) {{
                const law = payload.source === 'public_eis_html_223fz' ? '223fz' : '44fz';
                const searchUrlPayload = await fetchJson(`/api/demo/tender-agent/procurement/public-search-url?${{new URLSearchParams({{
                  query: String(payload.query || ''),
                  law,
                  region: String(payload.region || ''),
                  date_from: String(payload.date_from || ''),
                  date_to: String(payload.date_to || ''),
                }})}}`);
                state.procurementResults = [];
                document.getElementById('procurement-results').innerHTML = `
                  <div class="run-item">
                    <strong>Публичный HTML fallback</strong>
                    <p style="margin-top:10px">${{escapeHtml(searchUrlPayload.note)}}</p>
                    <div class="form-actions" style="margin-top:12px">
                      <a class="link-button" href="${{searchUrlPayload.eis_search_url}}" target="_blank" rel="noreferrer">Открыть поиск ЕИС</a>
                    </div>
                  </div>
                `;
                renderProcurementSourceDiagnostics(payload.source);
                setFlash('procurement-flash', 'Сформирована публичная ссылка поиска ЕИС. Выберите закупку вручную и затем используйте getDocsIP по номеру.');
                return;
              }}
              const response = await fetchJson('/api/demo/tender-agent/procurement/search', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(payload),
              }});
              state.procurementResults = response || [];
              renderProcurementResults();
              const selectedSource = payload.source || document.getElementById('procurement-source-select').value;
              renderProcurementSourceDiagnostics(selectedSource);
              setFlash('procurement-flash', `Поиск выполнен, найдено закупок: ${{state.procurementResults.length}}.`);
            }} catch (error) {{
              state.procurementResults = [];
              renderProcurementResults();
              await loadProcurementSources();
              setFlash('procurement-flash', `Не удалось выполнить поиск: ${{error.message}}`, true);
            }}
          }}

          async function createProcurementRun(procurementId, source, autoAnalyze = false) {{
            const activeQuery = new FormData(document.getElementById('procurement-search-form')).get('query') || '';
            setFlash('procurement-flash', `Создаём run для закупки ${{procurementId}}…`);
            try {{
              const payload = await fetchJson('/api/demo/tender-agent/runs/from-procurement', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ procurement_id: procurementId, source, query: String(activeQuery) }}),
              }});
              setFlash('procurement-flash', `Создан run: ${{payload.run_id}}. Статус документации: ${{attachmentsStatusLabel(payload.attachments_status)}}.`);
              await loadRuns();
              await selectRun(payload.run_id, true);
              if (autoAnalyze && payload.status !== 'docs_required') {{
                await analyzeRun(payload.run_id);
              }}
            }} catch (error) {{
              setFlash('procurement-flash', `Не удалось создать run: ${{error.message}}`, true);
            }}
          }}

          async function handleEisDocsArchive(event) {{
            event.preventDefault();
            clearFlash('eis-docs-flash');
            const form = event.currentTarget;
            const data = new FormData(form);
            const payload = {{
              reestr_number: String(data.get('reestr_number') || ''),
              law: String(data.get('law') || '44fz'),
              subsystem_type: String(data.get('subsystem_type') || 'PRIZ'),
              method: String(data.get('method') || 'getDocsByReestrNumber'),
              download_archive: data.get('download_archive') === 'on',
              analyze_after_download: data.get('analyze_after_download') === 'on',
            }};
            setFlash('eis-docs-flash', `Запрашиваем документацию по номеру ${{payload.reestr_number}} через getDocsIP…`);
            try {{
              const response = await fetchJson('/api/demo/tender-agent/runs/from-eis-docs-archive', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(payload),
              }});
              renderEisDocsResult(response);
              await loadProcurementSources();
              await loadRuns();
              await selectRun(response.run_id, true);
              if (payload.analyze_after_download && response.status !== 'docs_required') {{
                await analyzeRun(response.run_id);
                await selectRun(response.run_id, false);
              }}
              setFlash('eis-docs-flash', `Создан run ${{response.run_id}}. Статус документации: ${{attachmentsStatusLabel(response.attachments_status)}}. Статус архива: ${{displayValue(response.archive_download_status, 'не определён')}}.`);
            }} catch (error) {{
              await loadProcurementSources();
              renderEisDocsResult(null);
              setFlash('eis-docs-flash', `Не удалось получить документацию: ${{error.message}}`, true);
            }}
          }}

          function renderDatasetTenderCard(run) {{
            const tender = run.tender;
            document.getElementById('dataset-tender-card').innerHTML = `
              <h2>Карточка закупки</h2>
              <div class="grid-2">
                <div class="metric"><span class="metric-label">Название закупки</span><span class="metric-value">${{escapeHtml(tender.title)}}</span></div>
                <div class="metric"><span class="metric-label">Тип процедуры</span><span class="metric-value">${{escapeHtml(tender.procedure_type)}}</span></div>
                <div class="metric"><span class="metric-label">Заказчик</span><span class="metric-value">${{escapeHtml(tender.customer)}}</span></div>
                <div class="metric"><span class="metric-label">Категория</span><span class="metric-value">${{escapeHtml(tender.category)}}</span></div>
                <div class="metric"><span class="metric-label">Документы</span><span class="metric-value">${{tender.document_count}}</span></div>
                <div class="metric"><span class="metric-label">Требования</span><span class="metric-value">${{tender.requirement_count}}</span></div>
                <div class="metric"><span class="metric-label">Вопросы</span><span class="metric-value">${{tender.question_count}}</span></div>
                <div class="metric"><span class="metric-label">Рекомендация</span><span class="metric-value">${{escapeHtml(tender.final_recommendation_label)}}</span></div>
              </div>
            `;
          }}

          function renderSteps(nodeId, steps, displayStatuses = null) {{
            const node = document.getElementById(nodeId);
            if (!steps.length) {{
              node.innerHTML = `<div class="empty">Шаги ещё не готовы.</div>`;
              return;
            }}
            node.innerHTML = steps.map((step) => {{
              const status = displayStatuses?.get(step.key) || step.status;
              return `
                <div class="step-card">
                  <div class="step-top">
                    <div>
                      <strong>#${{step.order}} · ${{escapeHtml(step.title)}}</strong>
                      <div class="run-meta">${{escapeHtml(step.result_summary)}}</div>
                    </div>
                    <span class="status-chip ${{statusClass(status)}}">${{escapeHtml(statusLabel(status))}}</span>
                  </div>
                  <p>${{escapeHtml(step.agent_action)}}</p>
                  <div class="split" style="margin-top:12px">
                    <div>
                      <div class="section-title">Что найдено</div>
                      <ul>${{step.findings.map((item) => `<li>${{escapeHtml(item)}}</li>`).join('')}}</ul>
                    </div>
                    <div>
                      <div class="section-title">Что проверить человеку</div>
                      <ul>${{step.human_review.map((item) => `<li>${{escapeHtml(item)}}</li>`).join('')}}</ul>
                    </div>
                  </div>
                  <div class="trace" style="margin-top:12px">${{escapeHtml(step.trace)}}</div>
                </div>
              `;
            }}).join('');
          }}

          function renderDatasetSummary(run) {{
            const finalRecommendation = run.final_recommendation;
            document.getElementById('dataset-summary').innerHTML = `
              <div class="step-top">
                <div>
                  <h2>Финальная рекомендация</h2>
                  <p>Рекомендация: ${{escapeHtml(finalRecommendation.label)}}.</p>
                </div>
                <a class="link-button" href="/demo/tender-agent/report" target="_blank" rel="noreferrer">Открыть синтетический отчёт</a>
              </div>
              <div class="split">
                <div class="card" style="padding:16px">
                  <div class="section-title">Причины</div>
                  <ul>${{finalRecommendation.rationale.map((item) => `<li>${{escapeHtml(item)}}</li>`).join('')}}</ul>
                </div>
                <div class="card" style="padding:16px">
                  <div class="section-title">Ручные проверки</div>
                  <ul>${{finalRecommendation.manual_checks.map((item) => `<li>${{escapeHtml(item)}}</li>`).join('')}}</ul>
                </div>
              </div>
              <div class="trace" style="margin-top:14px">${{escapeHtml(finalRecommendation.trace)}}</div>
            `;
          }}

          async function loadDataset() {{
            state.datasetRun = await fetchJson('/api/demo/tender-agent/run');
            state.datasetDisplayStatuses = new Map(state.datasetRun.steps.map((step) => [step.key, step.status]));
            renderDatasetTenderCard(state.datasetRun);
            renderSteps('dataset-steps', state.datasetRun.steps, state.datasetDisplayStatuses);
            renderDatasetSummary(state.datasetRun);
          }}

          async function replayDataset() {{
            if (!state.datasetRun || state.datasetReplayActive) {{
              return;
            }}
            state.datasetReplayActive = true;
            state.datasetDisplayStatuses = new Map(state.datasetRun.steps.map((step) => [step.key, 'pending']));
            renderSteps('dataset-steps', state.datasetRun.steps, state.datasetDisplayStatuses);
            for (const step of state.datasetRun.steps) {{
              state.datasetDisplayStatuses.set(step.key, 'running');
              renderSteps('dataset-steps', state.datasetRun.steps, state.datasetDisplayStatuses);
              await new Promise((resolve) => window.setTimeout(resolve, 220));
              state.datasetDisplayStatuses.set(step.key, step.status);
              renderSteps('dataset-steps', state.datasetRun.steps, state.datasetDisplayStatuses);
              await new Promise((resolve) => window.setTimeout(resolve, 120));
            }}
            state.datasetReplayActive = false;
          }}

          function renderRunsList() {{
            const node = document.getElementById('runs-list');
            if (!state.uploadedRuns.length) {{
              node.innerHTML = `<div class="empty">Пока нет загруженных прогонов.</div>`;
              return;
            }}
            node.innerHTML = state.uploadedRuns.map((run) => `
              <div class="run-item${{run.run_id === state.selectedRunId ? ' active' : ''}}" data-run-id="${{escapeHtml(run.run_id)}}">
                <strong>${{escapeHtml(run.tender_title)}}</strong>
                <div class="run-meta">${{escapeHtml(run.run_id)}} · ${{escapeHtml(statusLabel(run.status))}} · файлов=${{run.file_count}}</div>
                <div class="run-meta">${{escapeHtml(run.procurement_source || run.mode)}}${{run.attachments_status ? ` · ${{escapeHtml(attachmentsStatusLabel(run.attachments_status))}}` : ''}}</div>
              </div>
            `).join('');
            for (const item of node.querySelectorAll('.run-item')) {{
              item.addEventListener('click', () => selectRun(item.dataset.runId, true));
            }}
          }}

          function renderSelectedRun(run) {{
            const reportLinks = run.report_html_url
              ? `<a class="link-button" href="${{run.report_html_url}}" target="_blank" rel="noreferrer">Открыть HTML-отчёт</a>
                 <a class="link-button" href="${{run.report_download_url}}">Скачать артефакт отчёта</a>`
              : `<span class="note">HTML-отчёт будет доступен после анализа.</span>`;
            const needsDocs = run.status === 'docs_required';
            const eisBlock = run.procurement_source === 'zakupki_gov_ru_getdocs_ip' ? `
              <div class="card" style="padding:16px">
                <div class="section-title">Источник: ЕИС getDocsIP</div>
                <div class="grid-2">
                  <div class="metric"><span class="metric-label">Реестровый номер</span><span class="metric-value">${{escapeHtml(displayValue(run.procurement_notice_number || run.procurement_id))}}</span></div>
                  <div class="metric"><span class="metric-label">SOAP method</span><span class="metric-value">${{escapeHtml(displayValue(run.soap_method))}}</span></div>
                  <div class="metric"><span class="metric-label">refId</span><span class="metric-value">${{escapeHtml(displayValue(run.eis_ref_id))}}</span></div>
                  <div class="metric"><span class="metric-label">Токен owner</span><span class="metric-value">${{escapeHtml(displayValue(run.token_owner))}}</span></div>
                  <div class="metric"><span class="metric-label">archiveUrl</span><span class="metric-value">${{booleanLabel(run.archive_url_present)}}</span></div>
                  <div class="metric"><span class="metric-label">Архив скачан</span><span class="metric-value">${{booleanLabel(run.archive_downloaded)}}</span></div>
                  <div class="metric"><span class="metric-label">Статус скачивания</span><span class="metric-value">${{escapeHtml(displayValue(run.archive_download_status))}}</span></div>
                  <div class="metric"><span class="metric-label">Распаковано документов</span><span class="metric-value">${{escapeHtml(displayValue(run.documents_extracted_count, '0'))}}</span></div>
                  <div class="metric"><span class="metric-label">Источник архива</span><span class="metric-value">${{escapeHtml(displayValue(run.archive_source_host && run.archive_source_path ? `${{run.archive_source_host}}${{run.archive_source_path}}` : null))}}</span></div>
                </div>
                <div class="note" style="margin-top:12px">Полный archive URL и ticket не отображаются в UI.</div>
              </div>
            ` : '';
            const procurementBlock = run.procurement_source ? `
              <div class="card" style="padding:16px">
                <div class="section-title">Источник закупки</div>
                <div class="grid-2">
                  <div class="metric"><span class="metric-label">Источник</span><span class="metric-value">${{escapeHtml(displayValue(run.procurement_source))}}</span></div>
                  <div class="metric"><span class="metric-label">Номер извещения</span><span class="metric-value">${{escapeHtml(displayValue(run.procurement_notice_number || run.procurement_id))}}</span></div>
                  <div class="metric"><span class="metric-label">Закон</span><span class="metric-value">${{escapeHtml(displayValue(run.procurement_law, 'не указан'))}}</span></div>
                  <div class="metric"><span class="metric-label">Статус документации</span><span class="metric-value">${{escapeHtml(attachmentsStatusLabel(run.attachments_status))}}</span></div>
                  <div class="metric"><span class="metric-label">Скачано/добавлено файлов</span><span class="metric-value">${{run.downloaded_files_count || run.files.length}}</span></div>
                  <div class="metric"><span class="metric-label">Ручная загрузка</span><span class="metric-value">${{booleanLabel(run.manual_upload_required)}}</span></div>
                  <div class="metric"><span class="metric-label">Ссылка на источник</span><span class="metric-value"><a class="inline-link" href="${{escapeHtml(displayValue(run.procurement_url, '#'))}}" target="_blank" rel="noreferrer">Открыть источник</a></span></div>
                </div>
              </div>
            ` : '';
            const manualUploadBlock = needsDocs ? `
              <div class="card" style="padding:16px">
                <div class="section-title">Ручная загрузка документов</div>
                <p>Автоматическое получение документации недоступно для этой закупки. Загрузите документы вручную, после чего run перейдёт в статус «готово к анализу».</p>
                <form id="manual-upload-form">
                  <label>
                    Файлы закупки
                    <input name="files" type="file" multiple required />
                  </label>
                  <div class="form-actions">
                    <button class="button primary" type="submit">Добавить документы в run</button>
                  </div>
                </form>
              </div>
            ` : '';
            const eventItems = (run.events || []).map((item) => `
              <li class="event-item">
                <div class="event-head">
                  <span>${{escapeHtml(item.timestamp || item.created_at)}} · ${{escapeHtml(item.step || 'Система')}}</span>
                  <span class="event-severity ${{escapeHtml(item.severity || 'info')}}">${{escapeHtml(item.severity || 'info')}}</span>
                </div>
                <div><strong>${{escapeHtml(item.event_type)}}</strong> · ${{escapeHtml(item.message_ru || item.message)}}</div>
              </li>
            `).join('');
            document.getElementById('selected-run-card').innerHTML = `
              <div class="step-top">
                <div>
                  <h2>${{escapeHtml(run.tender_title)}}</h2>
                  <p>${{escapeHtml(run.run_id)}} · ${{escapeHtml(statusLabel(run.status))}} · ${{escapeHtml(analysisModeLabel(run.analysis_mode))}}</p>
                </div>
                <div class="form-actions">
                  <button class="button primary" id="analyze-run-button" type="button"${{run.status === 'analyzing' || needsDocs ? ' disabled' : ''}}>Анализировать</button>
                </div>
              </div>
              <div class="grid-2">
                <div class="metric"><span class="metric-label">Категория</span><span class="metric-value">${{escapeHtml(run.tender_category)}}</span></div>
                <div class="metric"><span class="metric-label">Заказчик</span><span class="metric-value">${{escapeHtml(run.customer_name)}}</span></div>
                <div class="metric"><span class="metric-label">Файлов</span><span class="metric-value">${{run.files.length}}</span></div>
                <div class="metric"><span class="metric-label">Контроль человека</span><span class="metric-value">${{booleanLabel(run.human_in_the_loop)}}</span></div>
              </div>
              <div style="height:14px"></div>
              <div class="safety">
                <span>${{run.procurement_source ? 'Локальные и безопасно полученные публичные данные' : 'Только локально загруженные данные'}}</span>
                <span>Без внешних действий</span>
                <span>Без подачи на площадку</span>
                <span>Без отправки писем</span>
                <span>Без ЭЦП</span>
                <span>Требуется подтверждение человека</span>
              </div>
              <div style="height:14px"></div>
              <div class="split">
                <div>
                  <div class="section-title">Загруженные файлы</div>
                  <ul>${{run.files.map((item) => `<li>${{escapeHtml(item.display_name)}} · ${{escapeHtml(item.extension)}} · текст извлечён: ${{booleanLabel(item.extracted_text_available)}}</li>`).join('')}}</ul>
                </div>
                  <div>
                    <div class="section-title">Предупреждения и ограничения</div>
                    <ul>${{[...run.warnings, ...run.limitations].map((item) => `<li>${{escapeHtml(item)}}</li>`).join('')}}</ul>
                  </div>
                </div>
              <div style="height:14px"></div>
              ${{eisBlock}}
              <div style="height:14px"></div>
              ${{procurementBlock}}
              <div style="height:14px"></div>
              ${{manualUploadBlock}}
              <div style="height:14px"></div>
              <div class="form-actions">${{reportLinks}}</div>
              <div class="note" style="margin-top:12px">${{escapeHtml(run.uploaded_files_note || '')}}</div>
              <div style="height:14px"></div>
              <div class="card" style="padding:16px">
                <div class="section-title">Журнал работы агента</div>
                <ul class="event-list">${{eventItems || '<li class="event-item">Событий пока нет.</li>'}}</ul>
              </div>
              <div style="height:14px"></div>
              ${{renderQuoteSection(run)}}
              <div style="height:14px"></div>
              ${{renderEconomicsSection(run)}}
            `;
            const analyzeButton = document.getElementById('analyze-run-button');
            if (analyzeButton) {{
              analyzeButton.addEventListener('click', () => analyzeRun(run.run_id));
            }}
            const manualUploadForm = document.getElementById('manual-upload-form');
            if (manualUploadForm) {{
              manualUploadForm.addEventListener('submit', (event) => handleManualRunUpload(event, run.run_id));
            }}
          }}

          function renderSelectedRunSteps(run) {{
            if (!run.steps.length) {{
              document.getElementById('selected-run-steps').innerHTML = `
                <h2>Pipeline загруженного прогона</h2>
                <div class="empty">Пошаговый pipeline появится после запуска анализа.</div>
              `;
              return;
            }}
            const pipelineLabel = run.procurement_source
              ? 'Поиск закупки → Документация → Требования → Вопросы → RFQ → ТКП → Экономика → Риски → Решение'
              : 'Документы → Требования → Вопросы → RFQ → ТКП → Экономика → Риски → Решение';
            document.getElementById('selected-run-steps').innerHTML = `
              <div class="step-top">
                <div>
                  <h2>Pipeline загруженного прогона</h2>
                  <p>${{pipelineLabel}}</p>
                </div>
              </div>
              <div class="steps-list" id="uploaded-steps-body"></div>
            `;
            renderSteps('uploaded-steps-body', run.steps);
          }}

          function renderSelectedRunSummary(run) {{
            if (!run.final_recommendation) {{
              document.getElementById('selected-run-summary').innerHTML = `<div class="empty">Финальная рекомендация появится после завершения анализа.</div>`;
              return;
            }}
            const summary = run.final_recommendation;
            document.getElementById('selected-run-summary').innerHTML = `
              <div class="step-top">
                <div>
                  <h2>Финальная рекомендация</h2>
                  <p>Рекомендация: ${{escapeHtml(summary.label)}}.</p>
                </div>
                <span class="status-chip ${{statusClass(run.status)}}">${{escapeHtml(statusLabel(run.status))}}</span>
              </div>
              <div class="split">
                <div class="card" style="padding:16px">
                  <div class="section-title">Причины</div>
                  <ul>${{summary.rationale.map((item) => `<li>${{escapeHtml(item)}}</li>`).join('')}}</ul>
                </div>
                <div class="card" style="padding:16px">
                  <div class="section-title">Ручные проверки</div>
                  <ul>${{summary.manual_checks.map((item) => `<li>${{escapeHtml(item)}}</li>`).join('')}}</ul>
                </div>
                <div class="card" style="padding:16px">
                  <div class="section-title">Открытые вопросы</div>
                  <ul>${{summary.open_questions.map((item) => `<li>${{escapeHtml(item)}}</li>`).join('')}}</ul>
                </div>
                <div class="card" style="padding:16px">
                  <div class="section-title">Риски</div>
                  <ul>${{summary.risks.map((item) => `<li>${{escapeHtml(item)}}</li>`).join('')}}</ul>
                </div>
              </div>
              <div class="trace" style="margin-top:14px">${{escapeHtml(summary.trace)}}</div>
            `;
          }}

          async function loadRuns() {{
            const payload = await fetchJson('/api/demo/tender-agent/runs');
            state.uploadedRuns = payload.runs || [];
            renderRunsList();
            if (state.selectedRunId) {{
              const exists = state.uploadedRuns.some((item) => item.run_id === state.selectedRunId);
              if (exists) {{
                await selectRun(state.selectedRunId, false);
              }}
            }}
          }}

          async function selectRun(runId, switchTab) {{
            state.selectedRunId = runId;
            renderRunsList();
            const run = await fetchJson(`/api/demo/tender-agent/runs/${{encodeURIComponent(runId)}}`);
            renderSelectedRun(run);
            renderSelectedRunSteps(run);
            renderSelectedRunSummary(run);
            if (switchTab) {{
              document.querySelector('[data-tab="upload"]').click();
            }}
            if (window.history?.replaceState) {{
              window.history.replaceState(null, '', `/demo/tender-agent/runs/${{encodeURIComponent(runId)}}`);
            }}
          }}

          async function analyzeRun(runId) {{
            setFlash('upload-flash', `Запускаем анализ для ${{runId}}…`);
            try {{
              const payload = await fetchJson(`/api/demo/tender-agent/runs/${{encodeURIComponent(runId)}}/analyze`, {{
                method: 'POST',
              }});
              setFlash('upload-flash', `Анализ завершён: статус «${{statusLabel(payload.status)}}», режим «${{analysisModeLabel(payload.analysis_mode)}}».`);
              await loadRuns();
              await selectRun(runId, false);
            }} catch (error) {{
              setFlash('upload-flash', `Анализ не запущен: ${{error.message}}`, true);
            }}
          }}

          async function handleManualRunUpload(event, runId) {{
            event.preventDefault();
            setFlash('upload-flash', `Добавляем документы в run ${{runId}}…`);
            const form = event.currentTarget;
            const data = new FormData(form);
            try {{
              const response = await fetch(`/api/demo/tender-agent/runs/${{encodeURIComponent(runId)}}/files`, {{
                method: 'POST',
                body: data,
              }});
              if (!response.ok) {{
                let detail = `HTTP ${{response.status}}`;
                try {{
                  const payload = await response.json();
                  detail = payload.detail || detail;
                }} catch (_error) {{
                }}
                throw new Error(detail);
              }}
              const payload = await response.json();
              setFlash('upload-flash', `Документы добавлены. Новый статус: ${{statusLabel(payload.status)}}.`);
              await loadRuns();
              await selectRun(runId, false);
            }} catch (error) {{
              setFlash('upload-flash', `Не удалось добавить документы: ${{error.message}}`, true);
            }}
          }}

          async function handleUpload(event) {{
            event.preventDefault();
            clearFlash('upload-flash');
            const form = event.currentTarget;
            const data = new FormData(form);
            try {{
              const response = await fetch('/api/demo/tender-agent/runs', {{
                method: 'POST',
                body: data,
              }});
              if (!response.ok) {{
                let detail = `HTTP ${{response.status}}`;
                try {{
                  const payload = await response.json();
                  detail = payload.detail || detail;
                }} catch (_error) {{
                }}
                throw new Error(detail);
              }}
              const payload = await response.json();
              setFlash('upload-flash', `Создан демонстрационный прогон: ${{payload.run_id}}. Теперь можно запускать анализ.`);
              form.reset();
              await loadRuns();
              await selectRun(payload.run_id, true);
            }} catch (error) {{
              setFlash('upload-flash', `Не удалось создать прогон: ${{error.message}}`, true);
            }}
          }}

          async function bootstrap() {{
            wireTabs();
            document.getElementById('procurement-search-form').addEventListener('submit', handleProcurementSearch);
            document.getElementById('eis-docs-form').addEventListener('submit', handleEisDocsArchive);
            document.getElementById('replay-dataset').addEventListener('click', replayDataset);
            document.getElementById('upload-form').addEventListener('submit', handleUpload);
            await loadProcurementSources();
            await loadDataset();
            await loadRuns();
            if (state.selectedRunId) {{
              document.querySelector('[data-tab="upload"]').click();
            }}
            await handleProcurementSearch({{
              preventDefault() {{}},
              currentTarget: document.getElementById('procurement-search-form'),
            }});
          }}

          bootstrap().catch((error) => {{
            document.getElementById('dataset-tender-card').innerHTML = `<div class="empty">Не удалось загрузить демонстрационный интерфейс: ${{escapeHtml(error.message)}}</div>`;
          }});
        </script>
      </body>
    </html>
    """
