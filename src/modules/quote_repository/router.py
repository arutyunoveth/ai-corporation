from fastapi import APIRouter, Query, status

from src.modules.quote_repository.schemas import QuoteArtifactBindingResponse, QuoteResponse, QuoteSetResponse, RegisterQuoteRequest
from src.modules.quote_repository.service import get_quote, get_quote_set, list_quotes, register_quote
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["quotes"])


def _to_quote_response(result: tuple) -> QuoteResponse:
    quote, artifact_bindings = result
    return QuoteResponse(
        quote_id=quote.quote_id,
        quote_set_id=quote.quote_set_id,
        supplier_id=quote.supplier_id,
        rfq_id=quote.rfq_id,
        supplier_thread_id=quote.supplier_thread_id,
        quote_status=quote.quote_status,
        quoted_amount=quote.quoted_amount,
        currency_code=quote.currency_code,
        quoted_at=quote.quoted_at,
        notes=quote.notes,
        created_at=quote.created_at,
        updated_at=quote.updated_at,
        artifact_bindings=[QuoteArtifactBindingResponse.model_validate(item) for item in artifact_bindings],
    )


def _to_quote_set_response(result: tuple) -> QuoteSetResponse:
    quote_set, quotes = result
    return QuoteSetResponse(
        quote_set_id=quote_set.quote_set_id,
        deal_id=quote_set.deal_id,
        rfq_batch_id=quote_set.rfq_batch_id,
        created_at=quote_set.created_at,
        quotes=[_to_quote_response(item) for item in quotes],
    )


@router.post("/quotes/register", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
def register_quote_route(payload: RegisterQuoteRequest, session: DBSession) -> QuoteResponse:
    return _to_quote_response(get_quote(session, register_quote(session, payload).quote_id))


@router.get("/quotes/{quote_id}", response_model=QuoteResponse)
def get_quote_route(quote_id: str, session: DBSession) -> QuoteResponse:
    return _to_quote_response(get_quote(session, quote_id))


@router.get("/quotes", response_model=list[QuoteResponse])
def list_quotes_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[QuoteResponse]:
    return [_to_quote_response(item) for item in list_quotes(session, deal_id=deal_id)]


@router.get("/quote-sets/{quote_set_id}", response_model=QuoteSetResponse)
def get_quote_set_route(quote_set_id: str, session: DBSession) -> QuoteSetResponse:
    return _to_quote_set_response(get_quote_set(session, quote_set_id))
