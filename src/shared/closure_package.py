from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.cost_model.models import CostModelRecord, CostModelSet
from src.modules.execution_command.models import ExecutionCommandRecord, ExecutionCommandSet
from src.modules.incidents.models import IncidentRecord, IncidentSet
from src.modules.outcome_intake.service import get_outcome_intake_set
from src.modules.payment_collection.models import PaymentCollectionRecord, PaymentCollectionSet
from src.shared.errors import NotFoundError
from src.shared.validation import require_same_reference


@dataclass(slots=True)
class ClosurePackage:
    deal_id: str
    outcome_set: object
    outcome_record: object
    execution_set: object
    execution_record: object
    latest_payment_collection_set: object | None = None
    latest_payment_collection_record: object | None = None
    latest_cost_model_set: object | None = None
    latest_cost_model_record: object | None = None
    incident_count: int = 0


def load_closure_package(
    session: Session,
    *,
    deal_id: str,
    outcome_intake_set_id: str,
    execution_command_set_id: str,
) -> ClosurePackage:
    outcome_set, outcome_records = get_outcome_intake_set(session, outcome_intake_set_id)
    require_same_reference(deal_id, outcome_set.deal_id, "deal_id")
    if not outcome_records:
        raise NotFoundError(f"Outcome intake set '{outcome_intake_set_id}' has no persisted records")
    outcome_record = outcome_records[-1][0]

    execution_set = session.scalar(
        select(ExecutionCommandSet).where(ExecutionCommandSet.execution_command_set_id == execution_command_set_id)
    )
    if not execution_set:
        raise NotFoundError(f"Execution command set '{execution_command_set_id}' was not found")
    require_same_reference(deal_id, execution_set.deal_id, "deal_id")
    execution_record = session.scalar(
        select(ExecutionCommandRecord)
        .where(ExecutionCommandRecord.execution_command_set_id == execution_command_set_id)
        .order_by(ExecutionCommandRecord.created_at.desc(), ExecutionCommandRecord.id.desc())
        .limit(1)
    )
    if not execution_record:
        raise NotFoundError(f"Execution command set '{execution_command_set_id}' has no persisted records")

    latest_payment_collection_set = session.scalar(
        select(PaymentCollectionSet)
        .where(PaymentCollectionSet.deal_id == deal_id)
        .order_by(PaymentCollectionSet.created_at.desc(), PaymentCollectionSet.id.desc())
        .limit(1)
    )
    latest_payment_collection_record = None
    if latest_payment_collection_set:
        latest_payment_collection_record = session.scalar(
            select(PaymentCollectionRecord)
            .where(PaymentCollectionRecord.payment_collection_set_id == latest_payment_collection_set.payment_collection_set_id)
            .order_by(PaymentCollectionRecord.created_at.desc(), PaymentCollectionRecord.id.desc())
            .limit(1)
        )

    latest_cost_model_set = session.scalar(
        select(CostModelSet)
        .where(CostModelSet.deal_id == deal_id)
        .order_by(CostModelSet.created_at.desc(), CostModelSet.id.desc())
        .limit(1)
    )
    latest_cost_model_record = None
    if latest_cost_model_set:
        latest_cost_model_record = session.scalar(
            select(CostModelRecord)
            .where(CostModelRecord.cost_model_set_id == latest_cost_model_set.cost_model_set_id)
            .order_by(CostModelRecord.created_at.desc(), CostModelRecord.id.desc())
            .limit(1)
        )

    incident_count = int(
        session.scalar(
            select(func.count(IncidentRecord.id))
            .join(IncidentSet, IncidentSet.incident_set_id == IncidentRecord.incident_set_id)
            .where(IncidentSet.deal_id == deal_id)
        )
        or 0
    )

    return ClosurePackage(
        deal_id=deal_id,
        outcome_set=outcome_set,
        outcome_record=outcome_record,
        execution_set=execution_set,
        execution_record=execution_record,
        latest_payment_collection_set=latest_payment_collection_set,
        latest_payment_collection_record=latest_payment_collection_record,
        latest_cost_model_set=latest_cost_model_set,
        latest_cost_model_record=latest_cost_model_record,
        incident_count=incident_count,
    )
