import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from app.agent.worker import AutonomousAPWorker
from app.memory.execution_state import StateStore
from app.config import RUN_DIR, SCREENSHOT_DIR
from app.db import repositories as repo


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CentrAlign AI — Autonomous AP Worker",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ---------- Global ---------- */

    .stApp {
        background-color: #f7f8fa;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1450px;
    }

    /* ---------- Header ---------- */

    .hero {
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
        padding: 28px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
        border: 1px solid #374151;
    }

    .hero-title {
        color: white;
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .hero-subtitle {
        color: #d1d5db;
        font-size: 15px;
        margin-bottom: 0;
    }

    .hero-badge {
        display: inline-block;
        margin-top: 16px;
        padding: 6px 12px;
        border-radius: 20px;
        background-color: #065f46;
        color: #d1fae5;
        font-size: 12px;
        font-weight: 600;
    }

    /* ---------- Section headings ---------- */

    .section-title {
        font-size: 20px;
        font-weight: 700;
        color: #111827;
        margin-top: 10px;
        margin-bottom: 12px;
    }

    .section-description {
        color: #6b7280;
        font-size: 13px;
        margin-bottom: 15px;
    }

    /* ---------- Cards ---------- */

    .info-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }

    .metric-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 14px 16px;
        min-height: 105px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }

    .metric-label {
        color: #6b7280;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .metric-value {
        color: #111827;
        font-size: 23px;
        font-weight: 700;
        margin-top: 6px;
    }

    /* ---------- Status ---------- */

    .status-success {
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        color: #065f46;
        padding: 10px 14px;
        border-radius: 9px;
        font-weight: 600;
    }

    .status-warning {
        background: #fffbeb;
        border: 1px solid #fde68a;
        color: #92400e;
        padding: 10px 14px;
        border-radius: 9px;
        font-weight: 600;
    }

    .status-danger {
        background: #fef2f2;
        border: 1px solid #fecaca;
        color: #991b1b;
        padding: 10px 14px;
        border-radius: 9px;
        font-weight: 600;
    }

    .status-neutral {
        background: #f3f4f6;
        border: 1px solid #d1d5db;
        color: #374151;
        padding: 10px 14px;
        border-radius: 9px;
        font-weight: 600;
    }

    /* ---------- Policy ---------- */

    .policy-allowed {
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        border-radius: 10px;
        padding: 14px;
        color: #065f46;
    }

    .policy-blocked {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 10px;
        padding: 14px;
        color: #991b1b;
    }

    .policy-label {
        font-size: 11px;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    .policy-value {
        font-size: 18px;
        font-weight: 700;
        margin-top: 3px;
    }

    .policy-reason {
        font-size: 13px;
        margin-top: 7px;
        line-height: 1.5;
    }

    /* ---------- Approval ---------- */

    .approval-box {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        border-left: 5px solid #f97316;
        border-radius: 10px;
        padding: 16px 18px;
        margin: 14px 0;
    }

    .approval-title {
        color: #9a3412;
        font-size: 16px;
        font-weight: 700;
    }

    .approval-text {
        color: #7c2d12;
        font-size: 13px;
        margin-top: 5px;
        line-height: 1.5;
    }

    /* ---------- Trace ---------- */

    .trace-container {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 18px;
        max-height: 620px;
        overflow-y: auto;
    }

    .trace-step {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 9px 0;
        border-bottom: 1px solid #f3f4f6;
        font-size: 13px;
    }

    .trace-step:last-child {
        border-bottom: none;
    }

    .trace-icon {
        width: 22px;
        text-align: center;
        flex-shrink: 0;
    }

    .trace-event {
        font-weight: 700;
        color: #374151;
    }

    .trace-tool {
        color: #6b7280;
    }

    /* ---------- Evidence ---------- */

    .evidence-card {
        background: #111827;
        color: #f9fafb;
        border-radius: 10px;
        padding: 16px;
        font-family: monospace;
        font-size: 12px;
        overflow-x: auto;
    }

    /* ---------- Sidebar ---------- */

    [data-testid="stSidebar"] {
        background-color: #111827;
    }

    [data-testid="stSidebar"] * {
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] .stButton button {
        color: #111827 !important;
    }

    /* ---------- Buttons ---------- */

    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }

    /* ---------- Divider ---------- */

    hr {
        border: none;
        border-top: 1px solid #e5e7eb;
        margin: 24px 0;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "state" not in st.session_state:
    st.session_state.state = None

if "last_task" not in st.session_state:
    st.session_state.last_task = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="padding: 8px 0 20px 0;">
            <div style="
                font-size:22px;
                font-weight:700;
                color:white;
            ">
                CentrAlign AI
            </div>
            <div style="
                font-size:12px;
                color:#9ca3af;
                margin-top:4px;
            ">
                Autonomous Enterprise Worker
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.markdown("### Worker Controls")

    st.markdown(
        """
        <div style="
            background:#1f2937;
            padding:14px;
            border-radius:10px;
            font-size:13px;
            line-height:1.6;
        ">
            <b>Execution loop</b><br>
            Observe → Decide → Act<br>
            → Observe → Verify
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("")

    st.markdown(
        """
        <div style="
            background:#1f2937;
            padding:14px;
            border-radius:10px;
            font-size:13px;
            line-height:1.6;
        ">
            <b>Safety controls</b><br>
            • Deterministic policy gates<br>
            • Duplicate protection<br>
            • Human approval<br>
            • Retry handling<br>
            • Independent verification
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("")

    st.caption("Autonomous writes are blocked by deterministic enterprise policies.")


# ============================================================
# HERO HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">
            Autonomous Accounts Payable Worker
        </div>
        <div class="hero-subtitle">
            AI-powered invoice processing with policy controls,
            human oversight, recovery, and independent verification.
        </div>
        <div class="hero-badge">
            ● POLICY-BOUNDED AUTONOMY
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TASK INPUT
# ============================================================

st.markdown(
    '<div class="section-title">Business Task</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">'
    'Describe the business outcome you want the autonomous worker to achieve.'
    '</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns([4, 1])

with col1:

    task = st.text_area(
        "Business task",
        value="Find the latest invoice from ABC Office Supplies and process it.",
        height=105,
        label_visibility="collapsed",
        placeholder="Example: Find the latest invoice from ABC Office Supplies and process it.",
    )

with col2:

    st.markdown(
        """
        <div class="info-card" style="margin-top:2px;">
            <div class="metric-label">Approval threshold</div>
            <div class="metric-value" style="font-size:20px;">
                ₹100,000
            </div>
            <div style="font-size:12px;color:#6b7280;margin-top:5px;">
                Manager approval above threshold
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "▶  Start Worker",
        type="primary",
        use_container_width=True,
    ):
        worker = AutonomousAPWorker()
        st.session_state.state = worker.start(task)
        st.session_state.last_task = st.session_state.state.task_id
        st.rerun()


# ============================================================
# QUICK EXAMPLES
# ============================================================

st.markdown(
    """
    <div style="
        color:#6b7280;
        font-size:12px;
        margin-top:8px;
        margin-bottom:18px;
    ">
        Example scenarios: normal invoice · approval-required invoice · duplicate · conflict
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CURRENT STATE
# ============================================================

state = st.session_state.state

if state:

    st.divider()

    # --------------------------------------------------------
    # STATUS METRICS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">Execution Overview</div>',
        unsafe_allow_html=True,
    )

    tool_calls = len(
        [
            e
            for e in state.action_history
            if e.event_type == "TOOL_RESULT"
        ]
    )

    status_display = str(state.status).replace("_", " ").upper()

    verification_display = (
        str(state.verification_status).replace("_", " ").upper()
        if state.verification_status
        else "PENDING"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Worker Status</div>
                <div class="metric-value" style="font-size:18px;">
                    {status_display}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Tool Calls</div>
                <div class="metric-value">
                    {tool_calls}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Retries</div>
                <div class="metric-value">
                    {state.retry_count}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Verification</div>
                <div class="metric-value" style="font-size:17px;">
                    {verification_display}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("")


    # ========================================================
    # MAIN CONTENT
    # ========================================================

    left, right = st.columns([1, 1.05], gap="large")


    # ========================================================
    # LEFT COLUMN
    # ========================================================

    with left:

        # ----------------------------------------------------
        # INVOICE CONTEXT
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">Invoice Context</div>',
            unsafe_allow_html=True,
        )

        if state.extracted:

            extracted = state.extracted.model_dump(mode="json")

            st.markdown('<div class="info-card">', unsafe_allow_html=True)

            # Show important fields cleanly when available.
            vendor = extracted.get("vendor_name", "—")
            invoice_number = extracted.get("invoice_number", "—")
            invoice_date = extracted.get("invoice_date", "—")
            due_date = extracted.get("due_date", "—")
            total_amount = extracted.get("total_amount", "—")

            if isinstance(total_amount, (int, float)):
                amount_display = f"₹{total_amount:,.2f}"
            else:
                amount_display = str(total_amount)

            r1, r2 = st.columns(2)

            with r1:
                st.markdown("**Vendor**")
                st.write(vendor)

                st.markdown("**Invoice Number**")
                st.write(invoice_number)

                st.markdown("**Invoice Date**")
                st.write(invoice_date)

            with r2:
                st.markdown("**Due Date**")
                st.write(due_date)

                st.markdown("**Total Amount**")
                st.write(amount_display)

                st.markdown("**Record Status**")
                st.write(extracted.get("status", "—"))

            st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("View complete extracted data"):
                st.json(extracted)

        else:
            st.info("Invoice data not extracted yet.")


        # ----------------------------------------------------
        # POLICY
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">Policy Decision</div>',
            unsafe_allow_html=True,
        )

        policy_status = str(state.policy_status).upper()

        if policy_status == "ALLOWED":

            st.markdown(
                f"""
                <div class="policy-allowed">
                    <div class="policy-label">Policy Status</div>
                    <div class="policy-value">✓ ALLOWED</div>
                    <div class="policy-reason">
                        {state.policy_reason or "Within autonomous policy limits."}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        elif policy_status == "BLOCKED":

            st.markdown(
                f"""
                <div class="policy-blocked">
                    <div class="policy-label">Policy Status</div>
                    <div class="policy-value">✕ BLOCKED</div>
                    <div class="policy-reason">
                        {state.policy_reason or "Action blocked by enterprise policy."}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                f"""
                <div class="status-neutral">
                    Policy: {policy_status}
                </div>
                """,
                unsafe_allow_html=True,
            )


        # ----------------------------------------------------
        # HUMAN APPROVAL
        # ----------------------------------------------------

        if (
            state.approval_required
            and state.status == "WAITING_FOR_APPROVAL"
        ):

            st.markdown(
                f"""
                <div class="approval-box">
                    <div class="approval-title">
                        ⚠ Human Approval Required
                    </div>
                    <div class="approval-text">
                        {state.approval_reason}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            a, b = st.columns(2)

            with a:

                if st.button(
                    "✓ Approve",
                    type="primary",
                    use_container_width=True,
                ):

                    st.session_state.state = (
                        AutonomousAPWorker(state=state).resume(True)
                    )

                    st.rerun()

            with b:

                if st.button(
                    "✕ Deny",
                    use_container_width=True,
                ):

                    st.session_state.state = (
                        AutonomousAPWorker(state=state).resume(False)
                    )

                    st.rerun()


    # ========================================================
    # RIGHT COLUMN
    # ========================================================

    with right:

        # ----------------------------------------------------
        # EXECUTION TRACE
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">Execution Trace</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="section-description">'
            'Real-time record of decisions, tool execution, observations, and recovery.'
            '</div>',
            unsafe_allow_html=True,
        )

        trace_html = '<div class="trace-container">'

        for event in state.action_history:

            if event.status in {"ok", "success", "approved"}:
                icon = "✓"
                icon_color = "#059669"

            elif event.status in {"retrying", "pending"}:
                icon = "⚠"
                icon_color = "#d97706"

            else:
                icon = "✕"
                icon_color = "#dc2626"

            label = event.tool or event.event_type

            trace_html += f"""
                <div class="trace-step">
                    <div class="trace-icon"
                         style="color:{icon_color};font-weight:700;">
                        {icon}
                    </div>
                    <div>
                        <span class="trace-event">
                            {event.event_type}
                        </span>
                        <span class="trace-tool">
                            — {label}
                        </span>
                    </div>
                </div>
            """

        trace_html += "</div>"

        st.markdown(trace_html, unsafe_allow_html=True)


        # ----------------------------------------------------
        # EVIDENCE
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title" style="margin-top:22px;">Evidence</div>',
            unsafe_allow_html=True,
        )

        if state.ap_record_id:

            st.markdown(
                f"""
                <div class="info-card">
                    <div class="metric-label">AP Record ID</div>
                    <div class="metric-value" style="font-size:22px;">
                        #{state.ap_record_id}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if state.verification_evidence:

            with st.expander(
                "View expected vs actual verification",
                expanded=True,
            ):
                st.json(state.verification_evidence)


        # ----------------------------------------------------
        # ARTIFACTS
        # ----------------------------------------------------

        run_file = RUN_DIR / f"run_{state.task_id}.json"

        if run_file.exists():

            st.download_button(
                "↓  Download Execution JSON",
                run_file.read_bytes(),
                file_name=run_file.name,
                mime="application/json",
                use_container_width=True,
            )


        # ----------------------------------------------------
        # SCREENSHOTS
        # ----------------------------------------------------

        shots = list(
            SCREENSHOT_DIR.glob(
                f"*{state.task_id}*.png"
            )
        )

        if shots:

            with st.expander(
                f"Browser Evidence ({len(shots)} screenshot"
                + ("s" if len(shots) != 1 else "")
                + ")"
            ):

                for shot in shots:

                    st.image(
                        str(shot),
                        caption=shot.name,
                        use_container_width=True,
                    )


    # ========================================================
    # RUN SUMMARY
    # ========================================================

    st.divider()

    st.markdown(
        '<div class="section-title">Run Summary</div>',
        unsafe_allow_html=True,
    )

    if state.status == "COMPLETED":

        st.markdown(
            """
            <div class="status-success">
                ✓ Task completed and independently verified.
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif state.status == "WAITING_FOR_APPROVAL":

        st.markdown(
            """
            <div class="status-warning">
                ⚠ Worker paused safely and is waiting for human input.
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif state.status == "FAILED":

        st.markdown(
            f"""
            <div class="status-danger">
                ✕ Worker failed safely.<br>
                {state.failure_reason or "No additional failure information."}
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            f"""
            <div class="status-neutral">
                Worker status: {status_display}
            </div>
            """,
            unsafe_allow_html=True,
        )