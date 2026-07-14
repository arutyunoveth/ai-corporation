from src.modules.tender_operator_agent_demo.upload_service import (
    _extract_supply_items_from_notification_xml,
)


def test_notification_xml_extracts_duplicate_names_as_distinct_rows():
    xml = """
    <root xmlns:n="urn:test">
      <n:purchaseObject>
        <n:name>Папка пластиковая</n:name>
        <n:OKEI><n:code>796</n:code><n:nationalCode>ШТ</n:nationalCode></n:OKEI>
        <n:price>10.50</n:price><n:quantity>2</n:quantity><n:sum>21.00</n:sum>
        <n:type>PRODUCT</n:type>
      </n:purchaseObject>
      <n:purchaseObject>
        <n:name>Папка пластиковая</n:name>
        <n:OKEI><n:code>796</n:code><n:nationalCode>ШТ</n:nationalCode></n:OKEI>
        <n:price>12.00</n:price><n:quantity>5</n:quantity><n:sum>60.00</n:sum>
        <n:type>PRODUCT</n:type>
      </n:purchaseObject>
      <n:purchaseObject>
        <n:name>Техническое обслуживание</n:name>
        <n:OKEI><n:code>876</n:code><n:nationalCode>УСЛ ЕД</n:nationalCode></n:OKEI>
        <n:price>100.00</n:price><n:quantity>true</n:quantity><n:sum>100.00</n:sum>
        <n:type>SERVICE</n:type>
      </n:purchaseObject>
    </root>
    """

    items = _extract_supply_items_from_notification_xml(xml, "notice.xml")

    assert len(items) == 3
    assert [item.name for item in items[:2]] == ["Папка пластиковая", "Папка пластиковая"]
    assert [item.quantity for item in items[:2]] == ["2", "5"]
    assert [item.unit_price for item in items[:2]] == ["10,50", "12,00"]
    assert items[2].item_type == "service"
    assert items[2].quantity is None
