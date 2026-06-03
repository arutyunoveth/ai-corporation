from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.modules.quote_repository.service import get_quote_set
from src.modules.supplier_search.service import get_supplier_shortlist
from src.shared.validation import require_same_reference


@dataclass(slots=True)
class SupplierQualityPackage:
    deal_id: str
    shortlist: object
    shortlist_rows: list
    quote_set: object | None = None
    quotes: list | None = None


def load_supplier_quality_package(
    session: Session,
    *,
    deal_id: str,
    supplier_shortlist_id: str | None = None,
    quote_set_id: str | None = None,
) -> SupplierQualityPackage:
    shortlist = None
    shortlist_rows = []
    quote_set = None
    quotes = []

    if supplier_shortlist_id:
        shortlist, shortlist_rows = get_supplier_shortlist(session, supplier_shortlist_id)
        require_same_reference(deal_id, shortlist.deal_id, "deal_id")

    if quote_set_id:
        quote_set, quotes = get_quote_set(session, quote_set_id)
        require_same_reference(deal_id, quote_set.deal_id, "deal_id")

    return SupplierQualityPackage(
        deal_id=deal_id,
        shortlist=shortlist,
        shortlist_rows=shortlist_rows,
        quote_set=quote_set,
        quotes=quotes,
    )
