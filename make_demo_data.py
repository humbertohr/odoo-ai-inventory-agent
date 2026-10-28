
from pathlib import Path
import random
import pandas as pd

random.seed(42)

OUT = Path(__file__).resolve().parent / "demo_data"
OUT.mkdir(exist_ok=True)

risk_columns = [
    "product_id", "warehouse", "on_hand_inventory",
    "reserved_inventory", "available_inventory", "on_hand_quant",
    "reserved_quant", "available_quant", "on_hand_difference",
    "reserved_difference", "available_difference",
    "record_count_inventory", "record_count_quant", "record_status",
    "reconciliation_status", "review_priority",
    "requires_reconciliation_review", "agent_stock_confidence",
    "authoritative_stock_source", "latest_in_date_inventory",
    "latest_in_date_quant", "provisional_analysis_eligible",
    "transfer_eligible", "stock_baseline_status",
    "provisional_available_stock", "selected_stock_source",
    "transfer_block_reason", "outbound_units_90d", "outbound_lines_90d",
    "outbound_units_30d", "avg_daily_demand_90d",
    "avg_daily_demand_30d", "risk_stock_basis", "stockout_risk_status",
    "stock_values_agree", "provisional_stock_eligible",
    "days_of_stock_estimate", "demand_acceleration_flag",
    "provisional_risk_category", "recommendation_note",
]

validation_columns = [
    "product_odoo_id", "location_name", "on_hand_inventory",
    "reserved_inventory", "available_inventory", "on_hand_quant",
    "reserved_quant", "available_quant", "on_hand_difference",
    "reserved_difference", "available_difference",
    "record_count_inventory", "record_count_quant", "record_status",
    "reconciliation_status", "review_priority",
    "requires_reconciliation_review", "agent_stock_confidence",
    "authoritative_stock_source", "latest_in_date_inventory",
    "latest_in_date_quant", "validation_status", "agent_transfer_gate",
    "validated_available_stock", "may_recommend_transfer",
    "validation_timestamp_utc",
]

review_columns = [
    "product_id", "warehouse", "review_priority",
    "provisional_risk_category", "provisional_available_stock",
    "outbound_units_30d", "outbound_units_90d",
    "days_of_stock_estimate", "demand_acceleration_flag",
    "reason_for_review", "decision_status", "transfer_eligible",
]

risk_rows = []
validation_rows = []
review_rows = []

warehouses = ["WH/Stock", "WH/Secondary", "WH/East", "WH/West"]

for i in range(200):
    # Preserve the app's default selection with invented values.
    product_id = 4388 if i == 0 else 10000 + i
    warehouse = "WH/Stock" if i == 0 else warehouses[i % len(warehouses)]

    # Four deliberately varied reconciliation scenarios.
    if i % 10 in (0, 1, 2, 3):
        status = "SHARED_VALUES_MATCH"
        on_hand = random.randint(20, 250)
        reserved = random.randint(0, min(25, on_hand))
        quant_on_hand = on_hand
        quant_reserved = reserved
        validation_status = "VALIDATION_PENDING"
    elif i % 10 in (4, 5, 6):
        status = "SHARED_VALUES_DIFFER"
        on_hand = random.randint(30, 250)
        reserved = random.randint(0, min(20, on_hand))
        quant_on_hand = max(0, on_hand + random.choice([-12, -7, 8, 15]))
        quant_reserved = reserved
        validation_status = "BLOCKED_VALUE_MISMATCH"
    elif i % 10 in (7, 8):
        status = "ONLY_CURRENT_INVENTORY"
        on_hand = random.randint(10, 120)
        reserved = random.randint(0, min(10, on_hand))
        quant_on_hand = 0
        quant_reserved = 0
        validation_status = "BLOCKED_SOURCE_MISMATCH"
    else:
        status = "ONLY_QUANT"
        on_hand = 0
        reserved = 0
        quant_on_hand = random.randint(10, 120)
        quant_reserved = random.randint(0, min(10, quant_on_hand))
        validation_status = "BLOCKED_SOURCE_MISMATCH"

    available = max(0, on_hand - reserved)
    quant_available = max(0, quant_on_hand - quant_reserved)

    # All cases require review; no transfer authorization is permitted.
    mismatch = status != "SHARED_VALUES_MATCH"
    if mismatch:
        priority = "BLOCKED"
        gate = "BLOCKED_RECONCILIATION_REVIEW"
        risk_category = "BLOCKED_STOCK_VALIDATION"
        risk_status = "BLOCKED_RECONCILIATION_REVIEW"
    else:
        priority = random.choice(["HIGH", "MEDIUM", "URGENT"])
        gate = "BLOCKED_HUMAN_REVIEW"
        risk_category = "REVIEW_REQUIRED"
        risk_status = "BLOCKED_HUMAN_REVIEW"

    outbound_90d = random.randint(15, 450)
    outbound_30d = random.randint(5, min(180, outbound_90d))
    demand_90d = round(outbound_90d / 90, 3)
    demand_30d = round(outbound_30d / 30, 3)

    on_hand_diff = on_hand - quant_on_hand
    reserved_diff = reserved - quant_reserved
    available_diff = available - quant_available

    common = {
        "on_hand_inventory": on_hand,
        "reserved_inventory": reserved,
        "available_inventory": available,
        "on_hand_quant": quant_on_hand,
        "reserved_quant": quant_reserved,
        "available_quant": quant_available,
        "on_hand_difference": on_hand_diff,
        "reserved_difference": reserved_diff,
        "available_difference": available_diff,
        "record_count_inventory": 1 if status != "ONLY_QUANT" else 0,
        "record_count_quant": 1 if status != "ONLY_CURRENT_INVENTORY" else 0,
        "record_status": status,
        "reconciliation_status": status,
        "review_priority": priority,
        "requires_reconciliation_review": mismatch,
        "agent_stock_confidence": (
            "LOW_PENDING_RECONCILIATION" if mismatch
            else "RECONCILED_BETWEEN_EXPORTS"
        ),
        "authoritative_stock_source": "NOT_ESTABLISHED",
        "latest_in_date_inventory": "2026-10-01 00:00:00+00:00",
        "latest_in_date_quant": "2026-10-02 00:00:00+00:00",
    }

    risk_rows.append({
        "product_id": product_id,
        "warehouse": warehouse,
        **common,
        "provisional_analysis_eligible": False,
        "transfer_eligible": False,
        "stock_baseline_status": "UNCONFIRMED",
        "provisional_available_stock": None,
        "selected_stock_source": "NOT_ESTABLISHED",
        "transfer_block_reason": "Human review and source validation required",
        "outbound_units_90d": outbound_90d,
        "outbound_lines_90d": random.randint(3, 80),
        "outbound_units_30d": outbound_30d,
        "avg_daily_demand_90d": demand_90d,
        "avg_daily_demand_30d": demand_30d,
        "risk_stock_basis": "UNVALIDATED",
        "stockout_risk_status": risk_status,
        "stock_values_agree": not mismatch,
        "provisional_stock_eligible": False,
        "days_of_stock_estimate": None,
        "demand_acceleration_flag": demand_30d > demand_90d * 1.3,
        "provisional_risk_category": risk_category,
        "recommendation_note": (
            "Synthetic portfolio example; validate evidence and obtain "
            "authorized human review before any operational decision."
        ),
    })

    validation_rows.append({
        "product_odoo_id": product_id,
        "location_name": warehouse,
        **common,
        "validation_status": validation_status,
        "agent_transfer_gate": gate,
        "validated_available_stock": None,
        "may_recommend_transfer": False,
        "validation_timestamp_utc": "2026-10-28T00:00:00Z",
    })

    review_rows.append({
        "product_id": product_id,
        "warehouse": warehouse,
        "review_priority": priority,
        "provisional_risk_category": risk_category,
        "provisional_available_stock": None,
        "outbound_units_30d": outbound_30d,
        "outbound_units_90d": outbound_90d,
        "days_of_stock_estimate": None,
        "demand_acceleration_flag": demand_30d > demand_90d * 1.3,
        "reason_for_review": (
            "Synthetic demonstration case; reconcile sources and review manually."
        ),
        "decision_status": "REQUIRES_HUMAN_REVIEW",
        "transfer_eligible": False,
    })

pd.DataFrame(risk_rows, columns=risk_columns).to_csv(
    OUT / "stockout_risk_scored_v2.csv", index=False
)
pd.DataFrame(validation_rows, columns=validation_columns).to_csv(
    OUT / "inventory_validated_agent_input.csv", index=False
)
pd.DataFrame(review_rows, columns=review_columns).to_csv(
    OUT / "stockout_agent_review_queue_v1.csv", index=False
)

print("Synthetic demo datasets created successfully.")
print("Risk records:", len(risk_rows))
print("Validated records:", len(validation_rows))
print("Review queue cases:", len(review_rows))
print("Transfer-eligible cases:", sum(r["transfer_eligible"] for r in risk_rows))
print("All records are invented; no source CSVs were read.")
