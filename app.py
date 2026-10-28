
from pathlib import Path
import json

import pandas as pd
import streamlit as st

import re
import uuid
from datetime import datetime, timezone

from crewai import Agent, Crew, LLM, Process, Task

from inventory_safety import evaluate_inventory_safety


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

OUTPUT_DIR = Path(__file__).resolve().parent / "demo_data"

st.set_page_config(
    page_title="Odoo AI Inventory Operations Agent",
    page_icon="📦",
    layout="wide",
)


# --------------------------------------------------
# EXECUTIVE THEME — NAVY BLUE + STEEL BLUE
# --------------------------------------------------

st.markdown(
    """
    <style>
    /* ==============================================
       COLOR PALETTE
       Page:         #0E1117
       Panels:       #161B22
       Table cells:  #0E1117
       Table header: #1A1C24
       Borders:      #303640
       Accent:       #4C8BF5
       Highlight:    #8AB4F8
       Text:         #F0F4FA
       ============================================== */

    /* Main application background */
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .stApp {
        background-color: #0E1117 !important;
        color: #F0F4FA !important;
    }

    /* Main text */
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] li {
        color: #F0F4FA;
    }

    /* Headings */
    h1, h2, h3, h4 {
        color: #8AB4F8 !important;
        font-weight: 700 !important;
    }

    /* Header and sidebar */
    header[data-testid="stHeader"] {
        background-color: #0E1117 !important;
    }

    [data-testid="stSidebar"] {
        background-color: #161B22 !important;
    }

    /* KPI cards */
    [data-testid="stMetric"] {
        background-color: #161B22 !important;
        border: 1px solid #303640 !important;
        border-radius: 10px !important;
        padding: 16px !important;
    }

    [data-testid="stMetricLabel"] {
        color: #B8C7DC !important;
    }

    [data-testid="stMetricValue"] {
        color: #F0F4FA !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricDelta"] {
        color: #8AB4F8 !important;
    }

    /* Text inputs */
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] {
        background-color: #161B22 !important;
        border: 1px solid #303640 !important;
    }

    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea {
        background-color: #161B22 !important;
        color: #F0F4FA !important;
        -webkit-text-fill-color: #F0F4FA !important;
    }

    /* Select boxes */
    [data-baseweb="select"] > div {
        background-color: #161B22 !important;
        border-color: #303640 !important;
    }

    [data-baseweb="select"] * {
        color: #F0F4FA !important;
    }

    /* Dropdown menus */
    [role="listbox"],
    [role="option"] {
        background-color: #161B22 !important;
        color: #F0F4FA !important;
    }

    /* Buttons */
    .stButton > button {
        background-color: #2F6FDB !important;
        color: #FFFFFF !important;
        border: 1px solid #4C8BF5 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    .stButton > button:hover {
        background-color: #8AB4F8 !important;
        color: #0E1117 !important;
        border-color: #A9C7FA !important;
    }

    /* Table containers */
    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        background-color: #0E1117 !important;
        border: 1px solid #303640 !important;
        border-radius: 8px !important;
        overflow: hidden;
    }

    /* Standard HTML tables */
    [data-testid="stTable"] table,
    [data-testid="stTable"] thead,
    [data-testid="stTable"] tbody,
    [data-testid="stTable"] tr,
    [data-testid="stTable"] th,
    [data-testid="stTable"] td {
        background-color: #0E1117 !important;
        color: #F0F4FA !important;
        border-color: #303640 !important;
    }

    /* Interactive dataframe outer surface */
    [data-testid="stDataFrame"] {
        background-color: #0E1117 !important;
        border: 1px solid #303640 !important;
    }

    /* Dividers */
    hr {
        border-color: #303640 !important;
    }

    /* Expanders */
    [data-testid="stExpander"] {
        background-color: #161B22 !important;
        border: 1px solid #303640 !important;
        border-radius: 8px !important;
    }

    /* Links */
    a {
        color: #8AB4F8 !important;
    }

    /* Alerts retain their status backgrounds */
    [data-testid="stAlert"] {
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

@st.cache_data
def load_data():
    risk = pd.read_csv(
        OUTPUT_DIR / "stockout_risk_scored_v2.csv",
        low_memory=False,
    )

    validated = pd.read_csv(
        OUTPUT_DIR / "inventory_validated_agent_input.csv",
        low_memory=False,
    )

    review = pd.read_csv(
        OUTPUT_DIR / "stockout_agent_review_queue_v1.csv",
        low_memory=False,
    )

    return risk, validated, review


try:
    risk, validated, review = load_data()
except Exception as exc:
    st.error(f"Could not load inventory datasets: {exc}")
    st.stop()


# --------------------------------------------------
# HEADER AND DATASET OVERVIEW
# --------------------------------------------------

st.title("📦 Odoo AI Inventory Operations Agent")

st.caption(
    "Evidence-based inventory investigation | "
    "Historical CSV data | Human approval required"
)

st.info(
    "Inventory Intelligence | Evidence-based exception analysis, "
    "cross-source reconciliation, and risk assessment. "
    "All findings are based on historical Odoo exports and remain "
    "subject to inventory validation and authorized human review."
)

col1, col2, col3 = st.columns(3)

col1.metric("Risk records", f"{len(risk):,}")
col2.metric("Validated records", f"{len(validated):,}")
col3.metric("Review queue cases", f"{len(review):,}")

st.divider()


# --------------------------------------------------
# EXCEPTION MANAGEMENT TABLE
# --------------------------------------------------

st.subheader("Exception Management")
st.caption(
    "Search and prioritize inventory cases requiring review. "
    "Selecting a case below the table will be done using the "
    "product and warehouse selector that follows."
)

# Prepare review cases and attach reconciliation evidence.
review_table = review.copy()
risk_lookup = risk[
    [
        "product_id",
        "warehouse",
        "reconciliation_status",
        "agent_stock_confidence",
        "authoritative_stock_source",
    ]
].copy()

# Normalize join keys so CSV type differences do not prevent matches.
review_table["_product_key"] = (
    review_table["product_id"].astype(str).str.strip()
)
review_table["_warehouse_key"] = (
    review_table["warehouse"].astype(str).str.strip()
)

risk_lookup["_product_key"] = (
    risk_lookup["product_id"].astype(str).str.strip()
)
risk_lookup["_warehouse_key"] = (
    risk_lookup["warehouse"].astype(str).str.strip()
)

review_table = review_table.merge(
    risk_lookup[
        [
            "_product_key",
            "_warehouse_key",
            "reconciliation_status",
            "agent_stock_confidence",
            "authoritative_stock_source",
        ]
    ].drop_duplicates(
        subset=["_product_key", "_warehouse_key"]
    ),
    on=["_product_key", "_warehouse_key"],
    how="left",
    validate="many_to_one",
)

# Filters
filter_col1, filter_col2 = st.columns(2)

with filter_col1:
    priority_options = sorted(
        review_table["review_priority"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_priorities = st.multiselect(
        "Review priority",
        options=priority_options,
        default=priority_options,
        key="exception_priority_filter",
    )

with filter_col2:
    reconciliation_options = sorted(
        review_table["reconciliation_status"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_reconciliation = st.multiselect(
        "Reconciliation status",
        options=reconciliation_options,
        default=reconciliation_options,
        key="exception_reconciliation_filter",
    )

search_text = st.text_input(
    "Search product ID or warehouse",
    placeholder="e.g. 4388 or WH/Stock",
    key="exception_search",
)

filtered = review_table[
    review_table["review_priority"]
    .astype(str)
    .isin(selected_priorities)
    & review_table["reconciliation_status"]
    .astype(str)
    .isin(selected_reconciliation)
].copy()

if search_text.strip():
    query = search_text.strip().lower()

    search_mask = (
        filtered["product_id"].astype(str).str.lower().str.contains(
            query, regex=False, na=False
        )
        | filtered["warehouse"].astype(str).str.lower().str.contains(
            query, regex=False, na=False
        )
    )

    filtered = filtered.loc[search_mask]


# --------------------------------------------------
# EXECUTIVE OVERVIEW — FILTERED REVIEW CASES
# --------------------------------------------------

st.subheader("Executive Overview")
st.caption(
    "KPIs reflect the review cases currently visible after "
    "applying priority, reconciliation, and search filters."
)

blocked_count = (
    filtered["review_priority"]
    .astype(str)
    .eq("BLOCKED")
    .sum()
)

urgent_count = (
    filtered["review_priority"]
    .astype(str)
    .eq("URGENT")
    .sum()
)

negative_stock_count = (
    filtered["provisional_risk_category"]
    .astype(str)
    .eq("NEGATIVE_STOCK_REVIEW")
    .sum()
)

unresolved_source_count = (
    filtered["authoritative_stock_source"]
    .astype(str)
    .eq("NOT_ESTABLISHED")
    .sum()
)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        "Review cases",
        f"{len(filtered):,}",
    )

with kpi2:
    st.metric(
        "Blocked cases",
        f"{blocked_count:,}",
    )

with kpi3:
    st.metric(
        "Urgent cases",
        f"{urgent_count:,}",
    )

with kpi4:
    st.metric(
        "Negative stock",
        f"{negative_stock_count:,}",
    )

st.metric(
    "Unresolved inventory source",
    f"{unresolved_source_count:,}",
    help=(
        "Cases where the authoritative inventory source "
        "is recorded as NOT_ESTABLISHED."
    ),
)


# Display the table
display_columns = [
    "product_id",
    "warehouse",
    "review_priority",
    "provisional_risk_category",
    "reconciliation_status",
    "agent_stock_confidence",
    "reason_for_review",
    "decision_status",
    "transfer_eligible",
]

display_columns = [
    column for column in display_columns
    if column in filtered.columns
]


selection_event = st.dataframe(
    filtered[display_columns],
    hide_index=True,
    use_container_width=True,
    height=420,
    on_select="rerun",
    selection_mode="single-row",
    key="exception_review_table",
)

selected_rows = selection_event.selection.rows



if selected_rows:
    selected_case = filtered.iloc[selected_rows[0]]

    st.session_state["table_selected_case"] = (
        str(selected_case["product_id"]),
        str(selected_case["warehouse"]),
    )

    st.info(
        f"Selected case: Product {selected_case['product_id']} "
        f"| {selected_case['warehouse']}. "
        "The investigation selector will use this case."
    )




st.caption(
    "These are historical review records. Filtering or viewing "
    "a case does not authorize transfers, shipments, or adjustments."
)

st.divider()



# --------------------------------------------------
# PRODUCT AND WAREHOUSE SELECTION
# --------------------------------------------------

st.subheader("1. Select an inventory case")

choices = (
    risk[["product_id", "warehouse"]]
    .drop_duplicates()
    .sort_values(["product_id", "warehouse"])
    .reset_index(drop=True)
)

choices["case_label"] = choices.apply(
    lambda row: (
        f"Product {row['product_id']} | {row['warehouse']}"
    ),
    axis=1,
)

# Default case: Product 4388 | WH/Stock
default_matches = choices.index[
    pd.to_numeric(choices["product_id"], errors="coerce").eq(4388)
    & choices["warehouse"].astype(str).eq("WH/Stock")
].tolist()

default_index = default_matches[0] if default_matches else 0

# Synchronize the dropdown with the selected exception-table row.
table_case = st.session_state.get("table_selected_case")

if table_case is not None:
    table_product, table_warehouse = table_case

    table_matches = choices.index[
        choices["product_id"].astype(str).eq(table_product)
        & choices["warehouse"].astype(str).eq(table_warehouse)
    ].tolist()

    if table_matches:
        desired_label = choices.loc[
            table_matches[0], "case_label"
        ]

        if (
            st.session_state.get("inventory_case_selector")
            != desired_label
        ):
            st.session_state["inventory_case_selector"] = desired_label

# Initialize the dropdown before creating the widget.
if "inventory_case_selector" not in st.session_state:
    st.session_state["inventory_case_selector"] = (
        choices.loc[default_index, "case_label"]
    )

selected_label = st.selectbox(
    "Product and warehouse",
    options=choices["case_label"].tolist(),
    key="inventory_case_selector",
)

selected = choices.loc[
    choices["case_label"].eq(selected_label)
].iloc[0]

product_id = selected["product_id"]
warehouse = selected["warehouse"]


def find_case(df, product_col, warehouse_col):
    product = pd.to_numeric(df[product_col], errors="coerce")

    return df.loc[
        product.eq(float(product_id))
        & df[warehouse_col].astype(str).eq(str(warehouse))
    ]


case = find_case(risk, "product_id", "warehouse")
validation_case = find_case(
    validated, "product_odoo_id", "location_name"
)
review_case = find_case(review, "product_id", "warehouse")

if len(case) != 1 or len(validation_case) != 1:
    st.error(
        "Expected exactly one risk record and one validation "
        "record for this case. Investigation is disabled "
        "until the source records are resolved."
    )
    st.stop()

row = case.iloc[0]
validation_row = validation_case.iloc[0]

record = row.to_dict()
safety = evaluate_inventory_safety(record)


# --------------------------------------------------
# EVIDENCE COMPARISON
# --------------------------------------------------

st.subheader("2. Inventory evidence")

st.write(f"**Product:** {product_id}")
st.write(f"**Warehouse:** {warehouse}")

a, b, c = st.columns(3)

a.metric(
    "On hand — inventory snapshot",
    f"{row['on_hand_inventory']:,.0f}"
    if pd.notna(row["on_hand_inventory"]) else "N/A",
)

b.metric(
    "On hand — stock quant",
    f"{row['on_hand_quant']:,.0f}"
    if pd.notna(row["on_hand_quant"]) else "N/A",
)

c.metric(
    "On-hand difference",
    f"{row['on_hand_difference']:+,.0f}"
    if pd.notna(row["on_hand_difference"]) else "N/A",
)

a, b, c = st.columns(3)

a.metric(
    "Available — inventory snapshot",
    f"{row['available_inventory']:,.0f}"
    if pd.notna(row["available_inventory"]) else "N/A",
)

b.metric(
    "Available — stock quant",
    f"{row['available_quant']:,.0f}"
    if pd.notna(row["available_quant"]) else "N/A",
)

c.metric(
    "Available difference",
    f"{row['available_difference']:+,.0f}"
    if pd.notna(row["available_difference"]) else "N/A",
)

evidence_columns = [
    "reconciliation_status",
    "agent_stock_confidence",
    "authoritative_stock_source",
    "latest_in_date_inventory",
    "latest_in_date_quant",
    "stockout_risk_status",
    "transfer_eligible",
    "transfer_block_reason",
]

available_columns = [
    col for col in evidence_columns if col in row.index
]

st.dataframe(
    pd.DataFrame({
        "Field": available_columns,
        "Value": [str(row[col]) for col in available_columns],
    }),
    hide_index=True,
    use_container_width=True,
)

with st.expander("Validation gate evidence"):
    st.json({
        key: str(validation_row[key])
        for key in [
            "validation_status",
            "agent_transfer_gate",
            "validated_available_stock",
            "may_recommend_transfer",
        ]
        if key in validation_row.index
    })


# --------------------------------------------------
# SAFETY DECISION
# --------------------------------------------------

st.subheader("3. Independent Python safety decision")

st.error(f"**{safety.status}**")

st.write(
    f"May recommend transfer: **{safety.may_recommend_transfer}**"
)
st.write(
    "May authorize stock action: "
    f"**{safety.may_authorize_stock_action}**"
)

for reason in safety.reasons:
    st.write(f"- {reason}")

st.info(
    "Even when a case passes the data gates, human review "
    "and approval remain necessary. Matching values alone "
    "do not establish source authority."
)


# --------------------------------------------------
# CLAUDE INVESTIGATION AND AUDIT TRAIL
# --------------------------------------------------

st.subheader("4. AI investigation report")

current_case_key = f"{product_id}|{warehouse}"

if st.button(
    "Generate Claude investigation report",
    type="primary",
):
    import os

api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        api_key = None

if not api_key:
    st.error(
        "ANTHROPIC_API_KEY is unavailable. "
        "Configure the environment variable or Streamlit Secrets."
    )

    else:
        risk_fields = [
            "product_id",
            "warehouse",
            "on_hand_inventory",
            "on_hand_quant",
            "reserved_inventory",
            "reserved_quant",
            "available_inventory",
            "available_quant",
            "on_hand_difference",
            "available_difference",
            "reconciliation_status",
            "agent_stock_confidence",
            "authoritative_stock_source",
            "latest_in_date_inventory",
            "latest_in_date_quant",
            "stockout_risk_status",
            "provisional_risk_category",
            "transfer_eligible",
            "transfer_block_reason",
        ]

        validation_fields = [
            "validation_status",
            "agent_transfer_gate",
            "validated_available_stock",
            "may_recommend_transfer",
        ]

        evidence = {
            "source_files": [
                "stockout_risk_scored_v2.csv",
                "inventory_validated_agent_input.csv",
                "stockout_agent_review_queue_v1.csv",
            ],
            "risk_dataset": {
                key: str(row[key])
                for key in risk_fields
                if key in row.index
            },
            "validation_dataset": {
                key: str(validation_row[key])
                for key in validation_fields
                if key in validation_row.index
            },
            "python_safety_gate": {
                "status": safety.status,
                "may_recommend_transfer": (
                    safety.may_recommend_transfer
                ),
                "may_authorize_stock_action": (
                    safety.may_authorize_stock_action
                ),
                "reasons": safety.reasons,
            },
        }

        if not review_case.empty:
            review_row = review_case.iloc[0]

            evidence["review_queue"] = {
                key: str(review_row[key])
                for key in [
                    "review_priority",
                    "reason_for_review",
                    "decision_status",
                    "transfer_eligible",
                ]
                if key in review_row.index
            }

        with st.spinner(
            "Claude is investigating the supplied evidence..."
        ):
            try:
                llm = LLM(
                    model="anthropic/claude-sonnet-4-5",
                    temperature=0.1,
                )

                agent = Agent(
                    role="Odoo Inventory Investigation Analyst",
                    goal=(
                        "Produce accurate, evidence-based inventory "
                        "investigations without authorizing stock actions."
                    ),
                    backstory=(
                        "You investigate historical CSV evidence. "
                        "You distinguish facts from hypotheses and "
                        "never invent records or claim to have changed Odoo."
                    ),
                    llm=llm,
                    allow_delegation=False,
                    verbose=False,
                )

                task = Task(
                    description=f"""
Analyze the following historical inventory evidence:

{json.dumps(evidence, indent=2, ensure_ascii=False)}

Write these sections:
1. Confirmed facts
2. Discrepancies and uncertainty
3. Evidence still needed
4. Recommended investigation steps
5. Operational decision

Rules:
- Treat the data as historical CSV evidence, not live Odoo.
- The latest_in_date fields are stock-entry dates, not verified
  export timestamps. Do not infer source authority from them.
- Do not invent root causes, transactions, physical counts,
  approvals, or checks you did not perform.
- Do not interpret a lower reported quantity as a confirmed
  safe-to-ship quantity.
- Do not issue operational instructions or authorize stock actions.
  Any proposed restrictions or physical counts require human review.
- If the Python safety gate is blocked, state that transfer
  recommendations remain blocked.
- No inventory changes have been made.

Python safety decision:
{json.dumps(evidence["python_safety_gate"], indent=2)}
""",
                    expected_output=(
                        "An evidence-based investigation report with "
                        "facts, uncertainty, next steps, and decision."
                    ),
                    agent=agent,
                )

                crew = Crew(
                    agents=[agent],
                    tasks=[task],
                    process=Process.sequential,
                    verbose=False,
                )

                result = str(crew.kickoff())

                # Preserve the exact evidence and independent
                # safety decision used for this investigation.
                investigation_package = {
                    "case_key": current_case_key,
                    "product_id": str(product_id),
                    "warehouse": str(warehouse),
                    "generated_at_utc": (
                        datetime.now(timezone.utc).isoformat()
                    ),
                    "source_files": evidence["source_files"],
                    "evidence": evidence,
                    "safety_decision": {
                        "status": safety.status,
                        "may_recommend_transfer": (
                            safety.may_recommend_transfer
                        ),
                        "may_authorize_stock_action": (
                            safety.may_authorize_stock_action
                        ),
                        "reasons": safety.reasons,
                    },
                    "ai_report": result,
                    "inventory_changes_made": False,
                }

                st.session_state[
                    "investigation_package"
                ] = investigation_package

                st.success("Investigation report generated.")

            except Exception as exc:
                st.error(
                    f"Investigation failed: "
                    f"{type(exc).__name__}: {exc}"
                )


# --------------------------------------------------
# DISPLAY AND SAVE THE GENERATED INVESTIGATION
# --------------------------------------------------

package = st.session_state.get("investigation_package")

if package and package["case_key"] == current_case_key:
    st.markdown("### Investigation report")
    st.markdown(package["ai_report"])

    st.divider()
    st.markdown("### Independent Python safety decision")

    decision = package["safety_decision"]

    st.error(decision["status"])
    st.write(
        "May recommend transfer: "
        f"**{decision['may_recommend_transfer']}**"
    )
    st.write(
        "May authorize stock action: "
        f"**{decision['may_authorize_stock_action']}**"
    )

    for reason in decision["reasons"]:
        st.write(f"- {reason}")

    st.caption(
        "Historical evidence only. No inventory changes were made."
    )

    st.divider()
    st.markdown("### Save investigation")

    st.write(
        "Save the report and its evidence locally for audit "
        "and later review. Files are written only when you "
        "click the save button."
    )

    if st.button("Save investigation", type="secondary"):
        try:
            reports_dir = Path(__file__).parent / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            investigation_id = str(uuid.uuid4())
            saved_at = datetime.now(timezone.utc).isoformat()

            package_to_save = {
                **package,
                "investigation_id": investigation_id,
                "saved_at_utc": saved_at,
            }

            safe_warehouse = re.sub(
                r"[^A-Za-z0-9_-]+",
                "_",
                package["warehouse"],
            ).strip("_")

            filename_stem = (
                f"investigation_{package['product_id']}_"
                f"{safe_warehouse}_{investigation_id[:8]}"
            )

            json_path = reports_dir / f"{filename_stem}.json"
            md_path = reports_dir / f"{filename_stem}.md"

            # Create the structured JSON audit record.
            with json_path.open("w", encoding="utf-8") as file:
                json.dump(
                    package_to_save,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            # Create a readable Markdown report.
            markdown_report = f"""# Inventory Investigation Report

- **Investigation ID:** {investigation_id}
- **Product ID:** {package['product_id']}
- **Warehouse:** {package['warehouse']}
- **Generated at (UTC):** {package['generated_at_utc']}
- **Saved at (UTC):** {saved_at}

## Source files

{chr(10).join('- ' + name for name in package['source_files'])}

## Independent Python safety decision

- **Status:** {decision['status']}
- **May recommend transfer:** {decision['may_recommend_transfer']}
- **May authorize stock action:** {decision['may_authorize_stock_action']}

### Safety reasons

{chr(10).join('- ' + reason for reason in decision['reasons'])}

## AI investigation report

{package['ai_report']}

## Audit limitation

This investigation uses historical CSV evidence. It does not
establish live inventory, authorize operational actions, or
make changes in Odoo.
"""

            md_path.write_text(
                markdown_report,
                encoding="utf-8",
            )

            st.success("Investigation saved successfully.")

            st.write(f"**JSON audit record:** `{json_path}`")
            st.write(f"**Markdown report:** `{md_path}`")

            st.download_button(
                "Download JSON audit record",
                data=json.dumps(
                    package_to_save,
                    ensure_ascii=False,
                    indent=2,
                ),
                file_name=f"{filename_stem}.json",
                mime="application/json",
            )

            st.download_button(
                "Download Markdown report",
                data=markdown_report,
                file_name=f"{filename_stem}.md",
                mime="text/markdown",
            )

        except Exception as exc:
            st.error(
                f"Could not save investigation: "
                f"{type(exc).__name__}: {exc}"
            )
