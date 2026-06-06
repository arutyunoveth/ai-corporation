from src.modules.pilot_feedback.schemas import (
    FeedbackSource,
    FeedbackType,
    FinalDecision,
    NextAction,
)
from src.modules.pilot_feedback.service import create_feedback, create_outcome


class TestFeedbackCreation:
    def test_create_feedback(self):
        fb = create_feedback(
            partner_workspace_id="PW-001",
            export_package_id_or_pilot_run_id="EP-001",
            feedback_source=FeedbackSource.partner_call,
            feedback_type=FeedbackType.positive,
            usefulness_score=4,
            clarity_score=5,
            trust_score=4,
            would_pay_signal=True,
        )
        assert fb.feedback_id.startswith("FB-")
        assert fb.partner_workspace_id == "PW-001"
        assert fb.usefulness_score == 4
        assert fb.clarity_score == 5
        assert fb.trust_score == 4
        assert fb.would_pay_signal is True

    def test_create_feedback_defaults(self):
        fb = create_feedback(
            partner_workspace_id="PW-002",
            export_package_id_or_pilot_run_id="EP-002",
        )
        assert fb.feedback_source == FeedbackSource.operator_observation
        assert fb.feedback_type == FeedbackType.neutral
        assert fb.usefulness_score is None
        assert fb.clarity_score is None
        assert fb.trust_score is None
        assert fb.would_pay_signal is None
        assert fb.next_action == NextAction.iterate_report

    def test_create_feedback_with_minimal_scores(self):
        fb = create_feedback(
            partner_workspace_id="PW-003",
            export_package_id_or_pilot_run_id="EP-003",
            usefulness_score=1,
            clarity_score=1,
            trust_score=1,
        )
        assert fb.usefulness_score == 1
        assert fb.clarity_score == 1
        assert fb.trust_score == 1

    def test_create_feedback_with_max_scores(self):
        fb = create_feedback(
            partner_workspace_id="PW-004",
            export_package_id_or_pilot_run_id="EP-004",
            usefulness_score=5,
            clarity_score=5,
            trust_score=5,
        )
        assert fb.usefulness_score == 5
        assert fb.clarity_score == 5
        assert fb.trust_score == 5

    def test_would_pay_signal_false(self):
        fb = create_feedback(
            partner_workspace_id="PW-005",
            export_package_id_or_pilot_run_id="EP-005",
            would_pay_signal=False,
        )
        assert fb.would_pay_signal is False

    def test_would_pay_signal_none(self):
        fb = create_feedback(
            partner_workspace_id="PW-006",
            export_package_id_or_pilot_run_id="EP-006",
        )
        assert fb.would_pay_signal is None

    def test_feedback_with_qualitative_data(self):
        fb = create_feedback(
            partner_workspace_id="PW-007",
            export_package_id_or_pilot_run_id="EP-007",
            missing_information="pricing details",
            incorrect_or_unclear_sections="risk section",
            operator_notes="partner was confused about timeline",
        )
        assert fb.missing_information == "pricing details"
        assert fb.incorrect_or_unclear_sections == "risk section"
        assert fb.operator_notes == "partner was confused about timeline"

    def test_feedback_next_action_options(self):
        for action in NextAction:
            fb = create_feedback(
                partner_workspace_id="PW-008",
                export_package_id_or_pilot_run_id="EP-008",
                next_action=action,
            )
            assert fb.next_action == action


class TestOutcomeCreation:
    def test_create_outcome(self):
        oc = create_outcome(
            partner_workspace_id="PW-001",
            pilot_run_id="PR-001",
            final_decision=FinalDecision.offer_discounted_paid_pilot,
            decision_reason="Partner expressed willingness to pay after demo",
            conversion_readiness="high",
        )
        assert oc.outcome_id.startswith("OC-")
        assert oc.final_decision == FinalDecision.offer_discounted_paid_pilot
        assert oc.conversion_readiness == "high"

    def test_create_outcome_defaults(self):
        oc = create_outcome(
            partner_workspace_id="PW-002",
            pilot_run_id="PR-002",
        )
        assert oc.final_decision == FinalDecision.continue_design_partner
        assert oc.decision_reason == ""

    def test_outcome_with_full_data(self):
        oc = create_outcome(
            partner_workspace_id="PW-003",
            pilot_run_id="PR-003",
            final_decision=FinalDecision.not_ready,
            decision_reason="Reports need significant improvement",
            pilot_value_evidence="Partner did not complete review",
            conversion_readiness="low",
            recommended_next_step="Iterate report format and clarity before next pilot",
        )
        assert oc.final_decision == FinalDecision.not_ready
        assert oc.recommended_next_step == "Iterate report format and clarity before next pilot"

    def test_all_final_decisions(self):
        for decision in FinalDecision:
            oc = create_outcome(
                partner_workspace_id="PW-009",
                pilot_run_id="PR-009",
                final_decision=decision,
            )
            assert oc.final_decision == decision


class TestDP5ScoreValidation:
    def test_scores_within_range(self):
        fb = create_feedback(
            partner_workspace_id="PW-010",
            export_package_id_or_pilot_run_id="EP-010",
            usefulness_score=3,
            clarity_score=4,
            trust_score=2,
        )
        assert 1 <= fb.usefulness_score <= 5
        assert 1 <= fb.clarity_score <= 5
        assert 1 <= fb.trust_score <= 5


class TestDP5NoExternalAction:
    def test_no_external_actions(self):
        from src.modules.pilot_feedback import service, schemas
        assert hasattr(service, "create_feedback")
        assert hasattr(service, "create_outcome")
        assert hasattr(schemas, "FeedbackRecord")
        assert hasattr(schemas, "OutcomeRecord")
        assert hasattr(schemas, "FeedbackSource")
        assert hasattr(schemas, "FeedbackType")
        assert hasattr(schemas, "FinalDecision")
        assert hasattr(schemas, "NextAction")
        assert not hasattr(service, "send_survey")
        assert not hasattr(service, "integrate_crm")
