from __future__ import annotations

from xml.sax.saxutils import escape

from src.modules.tender_operator_agent_demo.procurement_schemas import ProcurementSearchRequest


SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
ZAKUPKI_NS = "http://zakupki.gov.ru/eis-integration/services-vbs"


def _token_header(token: str) -> str:
    return f"<zak:usertoken>{escape(token)}</zak:usertoken>"


def build_search_envelope(request: ProcurementSearchRequest, token: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:zak="{ZAKUPKI_NS}">
  <soapenv:Header>{_token_header(token)}</soapenv:Header>
  <soapenv:Body>
    <zak:searchProcurements>
      <zak:query>{escape(request.query)}</zak:query>
      <zak:law>{escape(request.law or "")}</zak:law>
      <zak:dateFrom>{escape(request.date_from or "")}</zak:dateFrom>
      <zak:dateTo>{escape(request.date_to or "")}</zak:dateTo>
      <zak:customerName>{escape(request.customer_name or "")}</zak:customerName>
      <zak:customerInn>{escape(request.customer_inn or "")}</zak:customerInn>
      <zak:region>{escape(request.region or "")}</zak:region>
      <zak:priceFrom>{"" if request.price_from is None else request.price_from}</zak:priceFrom>
      <zak:priceTo>{"" if request.price_to is None else request.price_to}</zak:priceTo>
      <zak:maxResults>{request.max_results}</zak:maxResults>
    </zak:searchProcurements>
  </soapenv:Body>
</soapenv:Envelope>"""


def build_details_envelope(procurement_id: str, token: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:zak="{ZAKUPKI_NS}">
  <soapenv:Header>{_token_header(token)}</soapenv:Header>
  <soapenv:Body>
    <zak:getProcurementDetails>
      <zak:procurementId>{escape(procurement_id)}</zak:procurementId>
    </zak:getProcurementDetails>
  </soapenv:Body>
</soapenv:Envelope>"""


def build_attachments_envelope(procurement_id: str, token: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:zak="{ZAKUPKI_NS}">
  <soapenv:Header>{_token_header(token)}</soapenv:Header>
  <soapenv:Body>
    <zak:listAttachments>
      <zak:procurementId>{escape(procurement_id)}</zak:procurementId>
    </zak:listAttachments>
  </soapenv:Body>
</soapenv:Envelope>"""
