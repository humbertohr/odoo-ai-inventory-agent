
from dataclasses import dataclass
from typing import Any


@dataclass
class SafetyDecision:
    status: str
    may_recommend_transfer: bool
    may_authorize_stock_action: bool
    reasons: list[str]


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "true", "1", "yes"
    }


def evaluate_inventory_safety(
    record: dict[str, Any],
) -> SafetyDecision:
    """
    Conservative decision gate for historical Odoo exports.

    This function does not modify inventory or authorize
    operational actions.
    """
    reasons = []

    reconciliation = str(
        record.get("reconciliation_status", "")
    ).strip().upper()

    confidence = str(
        record.get("agent_stock_confidence", "")
    ).strip().upper()

    authority = str(
        record.get("authoritative_stock_source", "")
    ).strip().upper()

    transfer_eligible = as_bool(
        record.get("transfer_eligible", False)
    )

    if reconciliation != "SHARED_VALUES_MATCH":
        reasons.append(
            f"Reconciliation is not a shared-value match: "
            f"{reconciliation or 'UNKNOWN'}."
        )

    if confidence != "RECONCILED_BETWEEN_EXPORTS":
        reasons.append(
            f"Confidence is not reconciled between exports: "
            f"{confidence or 'UNKNOWN'}."
        )

    if authority in {
        "", "NOT_ESTABLISHED", "NONE", "UNKNOWN"
    }:
        reasons.append(
            "Authoritative stock source is not established."
        )

    if not transfer_eligible:
        reasons.append(
            "Source dataset marks transfer eligibility as False."
        )

    permitted_for_human_review = (
        reconciliation == "SHARED_VALUES_MATCH"
        and confidence == "RECONCILED_BETWEEN_EXPORTS"
        and authority not in {
            "", "NOT_ESTABLISHED", "NONE", "UNKNOWN"
        }
        and transfer_eligible
    )

    if not permitted_for_human_review:
        return SafetyDecision(
            status="BLOCKED_HUMAN_REVIEW_REQUIRED",
            may_recommend_transfer=False,
            may_authorize_stock_action=False,
            reasons=reasons,
        )

    return SafetyDecision(
        status="ELIGIBLE_FOR_HUMAN_REVIEW",
        may_recommend_transfer=True,
        may_authorize_stock_action=False,
        reasons=[
            "Data gates passed. Human review and approval "
            "are still required before any operational action."
        ],
    )
