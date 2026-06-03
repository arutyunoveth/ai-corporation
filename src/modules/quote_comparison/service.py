from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.quote_comparison.models import (
    QuoteComparisonRecommendation,
    QuoteComparisonRow,
    QuoteComparisonSet,
)
from src.modules.quote_comparison.schemas import BuildQuoteComparisonRequest
from src.modules.quote_repository.models import QuoteRecord
from src.modules.supplier_verification.service import get_supplier_verification_set
from src.shared.db.base import utcnow
from src.shared.enums import (
    EventSeverity,
    QuoteComparisonStatus,
    QuoteStatus,
    SupplierVerificationResult,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_quote_comparison_set_id
from src.shared.quality_package import load_supplier_quality_package
from src.shared.validation import require_same_reference


def _get_set(session: Session, quote_comparison_set_id: str) -> QuoteComparisonSet:
    record = session.scalar(
        select(QuoteComparisonSet).where(QuoteComparisonSet.quote_comparison_set_id == quote_comparison_set_id)
    )
    if not record:
        raise NotFoundError(f"Quote comparison set '{quote_comparison_set_id}' was not found")
    return record


def _get_rows(session: Session, quote_comparison_set_id: str) -> list[QuoteComparisonRow]:
    return list(
        session.scalars(
            select(QuoteComparisonRow)
            .where(QuoteComparisonRow.quote_comparison_set_id == quote_comparison_set_id)
            .order_by(QuoteComparisonRow.rank_order.asc(), QuoteComparisonRow.id.asc())
        )
    )


def _get_recommendation(session: Session, quote_comparison_set_id: str) -> QuoteComparisonRecommendation | None:
    return session.scalar(
        select(QuoteComparisonRecommendation).where(
            QuoteComparisonRecommendation.quote_comparison_set_id == quote_comparison_set_id
        )
    )


def _quality_multiplier(result: str) -> float:
    if result == SupplierVerificationResult.PASS:
        return 1.0
    if result == SupplierVerificationResult.NEEDS_REVIEW:
        return 0.65
    return 0.2


def _quote_delivery_score(quote: QuoteRecord) -> float:
    if quote.quote_status == QuoteStatus.REVISED:
        return 92.0
    if quote.quote_status == QuoteStatus.RECEIVED:
        return 85.0
    return 10.0


def _price_scores(quotes: list[QuoteRecord]) -> dict[str, float]:
    active_quotes = [quote for quote in quotes if quote.quote_status != QuoteStatus.WITHDRAWN]
    if not active_quotes:
        return {quote.quote_id: 0.0 for quote in quotes}
    max_price = max(quote.quoted_amount for quote in active_quotes)
    min_price = min(quote.quoted_amount for quote in active_quotes)
    span = max(max_price - min_price, 1.0)
    scores: dict[str, float] = {}
    for quote in quotes:
        if quote.quote_status == QuoteStatus.WITHDRAWN:
            scores[quote.quote_id] = 0.0
            continue
        relative = (max_price - quote.quoted_amount) / span
        scores[quote.quote_id] = round(60.0 + 40.0 * relative, 2)
    return scores


def build_quote_comparison(session: Session, payload: BuildQuoteComparisonRequest) -> QuoteComparisonSet:
    package = load_supplier_quality_package(session, deal_id=payload.deal_id, quote_set_id=payload.quote_set_id)
    verification_set, verification_records = get_supplier_verification_set(session, payload.supplier_verification_set_id)
    require_same_reference(payload.deal_id, verification_set.deal_id, "deal_id")

    verification_map = {
        record.supplier_id: record for record, _flags in verification_records
    }
    quote_entries = [quote for quote, _bindings in package.quotes]
    if not quote_entries:
        raise ValidationError("Quote comparison requires a formal quote_set with quote records")

    comparison_set = QuoteComparisonSet(
        quote_comparison_set_id=next_quote_comparison_set_id(session, QuoteComparisonSet.quote_comparison_set_id),
        deal_id=payload.deal_id,
        quote_set_id=package.quote_set.quote_set_id,
        supplier_verification_set_id=verification_set.supplier_verification_set_id,
        comparison_status=QuoteComparisonStatus.BUILT,
    )
    session.add(comparison_set)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="quote_comparison_build_started",
        source_module_id="M-021",
        severity=EventSeverity.INFO,
        payload_json={
            "quote_comparison_set_id": comparison_set.quote_comparison_set_id,
            "quote_set_id": package.quote_set.quote_set_id,
            "supplier_verification_set_id": verification_set.supplier_verification_set_id,
        },
    )
    try:
        missing_verifications = [quote.supplier_id for quote in quote_entries if quote.supplier_id not in verification_map]
        if missing_verifications:
            raise ValidationError(
                f"Missing verification records for suppliers: {', '.join(sorted(set(missing_verifications)))}"
            )

        price_score_map = _price_scores(quote_entries)
        row_inputs: list[dict] = []
        for quote in quote_entries:
            verification = verification_map[quote.supplier_id]
            quality_score = round(verification.confidence_score * 100.0 * _quality_multiplier(str(verification.verification_result)), 2)
            delivery_score = _quote_delivery_score(quote)
            if quote.quote_status == QuoteStatus.WITHDRAWN:
                quality_score = min(quality_score, 20.0)
            total_score = round(price_score_map[quote.quote_id] * 0.45 + delivery_score * 0.15 + quality_score * 0.40, 2)
            comparison_notes = (
                f"Verification={verification.verification_result}; "
                f"confidence={verification.confidence_score:.2f}; "
                f"quote_status={quote.quote_status}."
            )
            row_inputs.append(
                {
                    "quote": quote,
                    "supplier_id": quote.supplier_id,
                    "price_score": price_score_map[quote.quote_id],
                    "delivery_score": delivery_score,
                    "quality_score": quality_score,
                    "total_score": total_score,
                    "comparison_notes": comparison_notes,
                }
            )

        row_inputs.sort(
            key=lambda item: (
                -item["total_score"],
                -item["quality_score"],
                item["quote"].quoted_amount,
                item["quote"].created_at,
            )
        )

        for index, row_input in enumerate(row_inputs, start=1):
            session.add(
                QuoteComparisonRow(
                    quote_comparison_set_id=comparison_set.quote_comparison_set_id,
                    quote_id=row_input["quote"].quote_id,
                    supplier_id=row_input["supplier_id"],
                    price_score=row_input["price_score"],
                    delivery_score=row_input["delivery_score"],
                    quality_score=row_input["quality_score"],
                    total_score=row_input["total_score"],
                    rank_order=index,
                    comparison_notes=row_input["comparison_notes"],
                )
            )

        winner = row_inputs[0]
        recommendation = QuoteComparisonRecommendation(
            quote_comparison_set_id=comparison_set.quote_comparison_set_id,
            recommended_quote_id=winner["quote"].quote_id,
            recommended_supplier_id=winner["supplier_id"],
            rationale=(
                f"Recommended quote has the highest total score ({winner['total_score']:.2f}) with "
                f"price={winner['price_score']:.2f}, delivery={winner['delivery_score']:.2f}, "
                f"quality={winner['quality_score']:.2f}."
            ),
        )
        session.add(recommendation)
        comparison_set.updated_at = utcnow()
        session.add(comparison_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="quote_comparison_built",
            source_module_id="M-021",
            severity=EventSeverity.INFO,
            payload_json={
                "quote_comparison_set_id": comparison_set.quote_comparison_set_id,
                "row_count": len(row_inputs),
                "recommended_quote_id": winner["quote"].quote_id,
            },
        )
        session.commit()
    except Exception as exc:
        comparison_set.comparison_status = QuoteComparisonStatus.FAILED
        comparison_set.updated_at = utcnow()
        session.add(comparison_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="quote_comparison_failed",
            source_module_id="M-021",
            severity=EventSeverity.HIGH,
            payload_json={
                "quote_comparison_set_id": comparison_set.quote_comparison_set_id,
                "error": str(exc),
            },
        )
        session.commit()
        raise
    session.refresh(comparison_set)
    return comparison_set


def get_quote_comparison_set(
    session: Session, quote_comparison_set_id: str
) -> tuple[QuoteComparisonSet, list[QuoteComparisonRow], QuoteComparisonRecommendation | None]:
    comparison_set = _get_set(session, quote_comparison_set_id)
    return comparison_set, _get_rows(session, quote_comparison_set_id), _get_recommendation(session, quote_comparison_set_id)


def list_quote_comparison_sets(
    session: Session, *, deal_id: str | None = None
) -> list[tuple[QuoteComparisonSet, list[QuoteComparisonRow], QuoteComparisonRecommendation | None]]:
    query = select(QuoteComparisonSet).order_by(QuoteComparisonSet.created_at.desc())
    if deal_id:
        query = query.where(QuoteComparisonSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_quote_comparison_set(session, item.quote_comparison_set_id) for item in sets]


def get_quote_comparison_recommendation(
    session: Session, quote_comparison_set_id: str
) -> QuoteComparisonRecommendation:
    recommendation = _get_recommendation(session, quote_comparison_set_id)
    if not recommendation:
        raise NotFoundError(f"Quote comparison recommendation for '{quote_comparison_set_id}' was not found")
    return recommendation
