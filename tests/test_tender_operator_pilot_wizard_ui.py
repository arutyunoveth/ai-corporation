def test_pilot_wizard_page_renders_simple_form(client):
    response = client.get("/pilot/tender-agent")

    assert response.status_code == 200
    assert "Поиск и анализ закупки" in response.text
    assert "Прогон тендера через формы" not in response.text
    assert "Ссылка на закупку в ЕИС или реестровый номер" in response.text
    assert "Поиск закупки по ключевым словам и фильтрам" in response.text
    assert "Расширенные фильтры" in response.text
    assert "Категория закупки" in response.text
    assert "223-ФЗ" in response.text
    assert "Капремонт" in response.text
    assert "Ключевые слова" in response.text
    assert "Статус закупки" in response.text
    assert "Способ закупки" in response.text
    assert "Срок подачи: от" in response.text
    assert "Сбросить фильтры" in response.text
    assert "Как это работает" not in response.text
    assert "Файл ТЗ / техническая спецификация" in response.text
    assert "Обработать тендер" in response.text
    assert "search-process-button" in response.text
    assert "/api/demo/tender-agent/runs/from-search-result" in response.text
    assert "/demo/tender-agent/assets/arvectum-logo-block.svg" in response.text
    assert "Pilot Wizard" not in response.text
    assert "Полный demo-console" not in response.text
    assert "Перейти к форме" not in response.text
    assert "Название закупки" not in response.text
    assert 'name="tender_title"' not in response.text
    assert 'name="customer_name"' not in response.text


def test_demo_console_links_to_pilot_wizard(client):
    response = client.get("/demo/tender-agent")

    assert response.status_code == 200
    assert "/pilot/tender-agent" in response.text
    assert "Пошаговый мастер" in response.text


def test_pilot_wizard_alias_renders(client):
    response = client.get("/demo/tender-agent/wizard")

    assert response.status_code == 200
    assert "Найдите закупку или вставьте ссылку / реестровый номер" in response.text
    assert "Найти закупки" in response.text
    assert "дд.мм.гггг" in response.text
    assert "НМЦК: от, ₽" in response.text
