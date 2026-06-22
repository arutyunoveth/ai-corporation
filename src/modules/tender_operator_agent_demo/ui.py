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
                <span class="badge">Демо-режим / human-in-the-loop</span>
                <span class="badge">Пилотный контур</span>
                <span class="badge">Без внешних действий</span>
              </div>
            </header>

            <div class="content">
              <div class="tabs">
                <button class="tab-button active" data-tab="dataset" type="button">Демо-набор</button>
                <button class="tab-button" data-tab="upload" type="button">Загрузка и анализ</button>
              </div>

              <section id="tab-dataset">
                <div class="layout">
                  <aside class="stack">
                    <div class="card" id="dataset-tender-card">
                      <div class="empty">Загрузка synthetic demo…</div>
                    </div>
                    <div class="card">
                      <h2>Ограничения демо</h2>
                      <div class="safety">
                        <span>Только synthetic demo data</span>
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
            </div>
          </div>
        </div>

        <script>
          const state = {{
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

          const statusClass = (status) => `status-${{status || 'pending'}}`;

          function statusLabel(status) {{
            return STEP_STATUS_LABELS[status] || RUN_STATUS_LABELS[status] || status || 'ожидает';
          }}

          function analysisModeLabel(mode) {{
            return ANALYSIS_MODE_LABELS[mode] || mode || 'не определено';
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
                            <td>${{item.needs_review ? 'нужна проверка' : 'ok'}}</td>
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

          function setFlash(message, isError = false) {{
            const node = document.getElementById('upload-flash');
            node.className = `flash${{isError ? ' error' : ''}}`;
            node.textContent = message;
            node.classList.remove('hidden');
          }}

          function clearFlash() {{
            const node = document.getElementById('upload-flash');
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
                document.getElementById('tab-dataset').classList.toggle('hidden', target !== 'dataset');
                document.getElementById('tab-upload').classList.toggle('hidden', target !== 'upload');
              }});
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
            document.getElementById('selected-run-card').innerHTML = `
              <div class="step-top">
                <div>
                  <h2>${{escapeHtml(run.tender_title)}}</h2>
                  <p>${{escapeHtml(run.run_id)}} · ${{escapeHtml(statusLabel(run.status))}} · ${{escapeHtml(analysisModeLabel(run.analysis_mode))}}</p>
                </div>
                <div class="form-actions">
                  <button class="button primary" id="analyze-run-button" type="button"${{run.status === 'analyzing' ? ' disabled' : ''}}>Анализировать</button>
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
                <span>Только локально загруженные данные</span>
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
              <div class="form-actions">${{reportLinks}}</div>
              <div class="note" style="margin-top:12px">${{escapeHtml(run.uploaded_files_note || '')}}</div>
              <div style="height:14px"></div>
              ${{renderQuoteSection(run)}}
              <div style="height:14px"></div>
              ${{renderEconomicsSection(run)}}
            `;
            const analyzeButton = document.getElementById('analyze-run-button');
            if (analyzeButton) {{
              analyzeButton.addEventListener('click', () => analyzeRun(run.run_id));
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
            document.getElementById('selected-run-steps').innerHTML = `
              <div class="step-top">
                <div>
                  <h2>Pipeline загруженного прогона</h2>
                  <p>Документы → Требования → Вопросы → RFQ → ТКП → Экономика → Риски → Решение</p>
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
            setFlash(`Запускаем анализ для ${{runId}}…`);
            const payload = await fetchJson(`/api/demo/tender-agent/runs/${{encodeURIComponent(runId)}}/analyze`, {{
              method: 'POST',
            }});
            setFlash(`Анализ завершён: статус «${{statusLabel(payload.status)}}», режим «${{analysisModeLabel(payload.analysis_mode)}}».`);
            await loadRuns();
            await selectRun(runId, false);
          }}

          async function handleUpload(event) {{
            event.preventDefault();
            clearFlash();
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
              setFlash(`Создан демонстрационный прогон: ${{payload.run_id}}. Теперь можно запускать анализ.`);
              form.reset();
              await loadRuns();
              await selectRun(payload.run_id, true);
            }} catch (error) {{
              setFlash(`Не удалось создать прогон: ${{error.message}}`, true);
            }}
          }}

          async function bootstrap() {{
            wireTabs();
            document.getElementById('replay-dataset').addEventListener('click', replayDataset);
            document.getElementById('upload-form').addEventListener('submit', handleUpload);
            await loadDataset();
            await loadRuns();
          }}

          bootstrap().catch((error) => {{
            document.getElementById('dataset-tender-card').innerHTML = `<div class="empty">Не удалось загрузить демонстрационный интерфейс: ${{escapeHtml(error.message)}}</div>`;
          }});
        </script>
      </body>
    </html>
    """
