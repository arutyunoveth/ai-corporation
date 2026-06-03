from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.bid_packages.models import BidPackageRecord, BidPackageSet
from src.modules.outcome_intake.service import get_outcome_intake_set
from src.modules.quote_comparison.models import (
    QuoteComparisonRecommendation,
    QuoteComparisonSet,
)
from src.modules.quote_repository.models import QuoteRecord
from src.shared.errors import NotFoundError
from src.shared.validation import require_same_reference


@dataclass(slots=True)
class ExecutionPackage:
    deal_id: str
    outcome_set: object
    outcome_record: object
    quote_comparison_set: object | None = None
    quote_recommendation: object | None = None
    recommended_quote: object | None = None
    latest_bid_package_set: object | None = None
    latest_bid_package_record: object | None = None


def load_execution_package(
    session: Session,
    *,
    deal_id: str,
    outcome_intake_set_id: str,
) -> ExecutionPackage:
    outcome_set, outcome_records = get_outcome_intake_set(session, outcome_intake_set_id)
    require_same_reference(deal_id, outcome_set.deal_id, "deal_id")
    if not outcome_records:
        raise NotFoundError(f"Outcome intake set '{outcome_intake_set_id}' has no persisted records")

    outcome_record = outcome_records[-1][0]
    latest_comparison = session.scalar(
        select(QuoteComparisonSet)
        .where(QuoteComparisonSet.deal_id == deal_id)
        .order_by(QuoteComparisonSet.created_at.desc(), QuoteComparisonSet.id.desc())
        .limit(1)
    )
    recommendation = None
    recommended_quote = None
    if latest_comparison:
        recommendation = session.scalar(
            select(QuoteComparisonRecommendation).where(
                QuoteComparisonRecommendation.quote_comparison_set_id == latest_comparison.quote_comparison_set_id
            )
        )
        if recommendation:
            recommended_quote = session.scalar(
                select(QuoteRecord).where(QuoteRecord.quote_id == recommendation.recommended_quote_id)
            )

    latest_bid_package_set = session.scalar(
        select(BidPackageSet)
        .where(BidPackageSet.deal_id == deal_id)
        .order_by(BidPackageSet.created_at.desc(), BidPackageSet.id.desc())
        .limit(1)
    )
    latest_bid_package_record = None
    if latest_bid_package_set:
        latest_bid_package_record = session.scalar(
            select(BidPackageRecord)
            .where(BidPackageRecord.bid_package_set_id == latest_bid_package_set.bid_package_set_id)
            .order_by(BidPackageRecord.package_version_no.desc(), BidPackageRecord.id.desc())
            .limit(1)
        )

    return ExecutionPackage(
        deal_id=deal_id,
        outcome_set=outcome_set,
        outcome_record=outcome_record,
        quote_comparison_set=latest_comparison,
        quote_recommendation=recommendation,
        recommended_quote=recommended_quote,
        latest_bid_package_set=latest_bid_package_set,
        latest_bid_package_record=latest_bid_package_record,
    )
