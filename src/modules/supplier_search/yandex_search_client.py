from __future__ import annotations

from dataclasses import dataclass, field
from xml.etree import ElementTree

import httpx

YT_SEARCH_API_URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"


@dataclass
class YandexSearchResult:
    title: str
    url: str
    snippet: str
    domain: str


@dataclass
class YandexSearchResponse:
    items: list[YandexSearchResult] = field(default_factory=list)
    total: int = 0
    error: str | None = None
    raw_xml: str | None = None


class YandexSearchClient:
    def __init__(self, api_key: str, folder_id: str, timeout: int = 30):
        self._api_key = api_key
        self._folder_id = folder_id
        self._timeout = timeout

    def search(self, query: str, max_results: int = 10) -> YandexSearchResponse:
        payload = {
            "query": {
                "searchType": "SEARCH_TYPE_RU",
                "queryText": query,
                "maxResults": max_results,
            },
            "folderId": self._folder_id,
            "responseFormat": "FORMAT_XML",
        }
        headers = {
            "Authorization": f"Api-Key {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(YT_SEARCH_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                return YandexSearchResponse(error=f"HTTP {resp.status_code}: {resp.text[:200]}")
            body = resp.json()
            raw_b64 = body.get("rawData")
            if not raw_b64:
                return YandexSearchResponse(error="No rawData in response")
            import base64
            raw_xml = base64.b64decode(raw_b64).decode("utf-8", errors="replace")
            return self._parse_xml(raw_xml)
        except Exception as e:
            return YandexSearchResponse(error=str(e))

    def _parse_xml(self, raw_xml: str) -> YandexSearchResponse:
        results: list[YandexSearchResult] = []
        try:
            root = ElementTree.fromstring(raw_xml)
            ns = self._guess_ns(root.tag)
            response_node = root if not ns else root
            found = response_node.find(f".//{{{ns}}}found" if ns else ".//found")
            total = int(found.text) if found is not None and found.text else 0
            for group_elem in response_node.findall(f".//{{{ns}}}group" if ns else ".//group"):
                doc_elem = group_elem.find(f".//{{{ns}}}doc" if ns else ".//doc")
                if doc_elem is None:
                    continue
                title = _elem_text(doc_elem, "title", ns)
                url = _elem_text(doc_elem, "url", ns)
                domain = _elem_text(doc_elem, "domain", ns)
                snippet = _elem_text(doc_elem, "passage", ns) or ""
                results.append(YandexSearchResult(title=title, url=url, snippet=snippet, domain=domain))
            return YandexSearchResponse(items=results, total=total, raw_xml=raw_xml)
        except Exception as e:
            return YandexSearchResponse(error=f"XML parse error: {e}", raw_xml=raw_xml)

    @staticmethod
    def _guess_ns(tag: str) -> str:
        idx = tag.find("}")
        return tag[1:idx] if idx != -1 else ""


def _elem_text(parent: ElementTree.Element, tag: str, ns: str) -> str:
    el = parent.find(f"{{{ns}}}{tag}" if ns else tag)
    return el.text or "" if el is not None else ""
