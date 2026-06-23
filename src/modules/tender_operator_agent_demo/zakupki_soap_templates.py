from __future__ import annotations

from xml.sax.saxutils import escape

from src.modules.tender_operator_agent_demo.procurement_schemas import ProcurementSearchRequest


SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
LEGACY_ZAKUPKI_NS = "http://zakupki.gov.ru/eis-integration/services-vbs"


def _legacy_token_header(token: str) -> str:
    return f"<zak:usertoken>{escape(token)}</zak:usertoken>"


def build_search_envelope(request: ProcurementSearchRequest, token: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:zak="{LEGACY_ZAKUPKI_NS}">
  <soapenv:Header>{_legacy_token_header(token)}</soapenv:Header>
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
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:zak="{LEGACY_ZAKUPKI_NS}">
  <soapenv:Header>{_legacy_token_header(token)}</soapenv:Header>
  <soapenv:Body>
    <zak:getProcurementDetails>
      <zak:procurementId>{escape(procurement_id)}</zak:procurementId>
    </zak:getProcurementDetails>
  </soapenv:Body>
</soapenv:Envelope>"""


def build_attachments_envelope(procurement_id: str, token: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:zak="{LEGACY_ZAKUPKI_NS}">
  <soapenv:Header>{_legacy_token_header(token)}</soapenv:Header>
  <soapenv:Body>
    <zak:listAttachments>
      <zak:procurementId>{escape(procurement_id)}</zak:procurementId>
    </zak:listAttachments>
  </soapenv:Body>
</soapenv:Envelope>"""


def build_get_docs_by_reestr_number_envelope(
    *,
    token: str,
    namespace: str,
    token_header_name: str,
    request_id: str,
    created_time: str,
    mode: str,
    reestr_number: str,
    subsystem_type: str = "PRIZ",
) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:ws="{escape(namespace)}">
  <soapenv:Header>
    <{escape(token_header_name)}>{escape(token)}</{escape(token_header_name)}>
  </soapenv:Header>
  <soapenv:Body>
    <ws:getDocsByReestrNumberRequest>
      <index>
        <id>{escape(request_id)}</id>
        <createDateTime>{escape(created_time)}</createDateTime>
        <mode>{escape(mode)}</mode>
      </index>
      <selectionParams>
        <subsystemType>{escape(subsystem_type)}</subsystemType>
        <reestrNumber>{escape(reestr_number)}</reestrNumber>
      </selectionParams>
    </ws:getDocsByReestrNumberRequest>
  </soapenv:Body>
</soapenv:Envelope>"""


def build_get_nsi_envelope(
    *,
    token: str,
    namespace: str,
    token_header_name: str,
    request_id: str,
    created_time: str,
    mode: str,
    nsi_code44: str = "nsiAllList",
    nsi_kind: str = "all",
) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:ws="{escape(namespace)}">
  <soapenv:Header>
    <{escape(token_header_name)}>{escape(token)}</{escape(token_header_name)}>
  </soapenv:Header>
  <soapenv:Body>
    <ws:getNsiRequest>
      <index>
        <id>{escape(request_id)}</id>
        <createDateTime>{escape(created_time)}</createDateTime>
        <mode>{escape(mode)}</mode>
      </index>
      <selectionParams>
        <nsiCode44>{escape(nsi_code44)}</nsiCode44>
        <nsiKind>{escape(nsi_kind)}</nsiKind>
      </selectionParams>
    </ws:getNsiRequest>
  </soapenv:Body>
</soapenv:Envelope>"""


def build_get_docs_by_org_region_envelope(
    *,
    token: str,
    namespace: str,
    token_header_name: str,
    request_id: str,
    created_time: str,
    mode: str,
    org_region: str,
    exact_date: str,
    document_type44: str,
    subsystem_type: str = "PRIZ",
) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:ws="{escape(namespace)}">
  <soapenv:Header>
    <{escape(token_header_name)}>{escape(token)}</{escape(token_header_name)}>
  </soapenv:Header>
  <soapenv:Body>
    <ws:getDocsByOrgRegionRequest>
      <index>
        <id>{escape(request_id)}</id>
        <createDateTime>{escape(created_time)}</createDateTime>
        <mode>{escape(mode)}</mode>
      </index>
      <selectionParams>
        <orgRegion>{escape(org_region)}</orgRegion>
        <subsystemType>{escape(subsystem_type)}</subsystemType>
        <documentType44>{escape(document_type44)}</documentType44>
        <periodInfo>
          <exactDate>{escape(exact_date)}</exactDate>
        </periodInfo>
      </selectionParams>
    </ws:getDocsByOrgRegionRequest>
  </soapenv:Body>
</soapenv:Envelope>"""
