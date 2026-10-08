import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.experiment import ExperimentConfig, assign_variant, AuditLog
from engine.simulator import SCENARIOS, simulate_calls, replay_in_batches
from engine.stats import decide, compare_binary_rates


st.set_page_config(
    page_title="VoicePilot",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
st.markdown(
    """
<style>
.block-container {max-width: 1400px; padding-top: 1.5rem;}
.hero {
    padding: 1.4rem 1.6rem;
    border-radius: 18px;
    background: linear-gradient(135deg, #101827 0%, #172554 100%);
    color: white;
    margin-bottom: 1rem;
}
.hero h1 {margin:0 0 .35rem 0; font-size: 2.1rem;}
.hero p {margin:0; color:#dbeafe;}
.metric-card {
    border:1px solid #e5e7eb;
    border-radius:16px;
    padding:1rem;
    background:white;
}
.small {color:#64748b;font-size:.85rem;}
.decision {
    border-radius:14px;
    padding:1rem 1.2rem;
    font-weight:700;
    font-size:1.2rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
<h1>VoicePilot — AI Voice Agent Experimentation & Safe Rollout</h1>
<p>Evidence-based prompt experimentation: test small → measure honestly → ship only when it wins.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
st.sidebar.header("Experiment")
scenario_name = st.sidebar.selectbox(
    "Demo scenario",
    list(SCENARIOS.keys()),
    index=0,
)

scenario = SCENARIOS[scenario_name]

split_pct = st.sidebar.slider(
    "Treatment traffic (B)",
    min_value=5,
    max_value=50,
    value=10,
    step=5,
)
split_b = split_pct / 100

min_per_arm = st.sidebar.number_input(
    "Minimum samples / arm",
    min_value=100,
    max_value=10000,
    value=1000,
    step=100,
)

max_looks = st.sidebar.number_input(
    "Planned statistical looks",
    min_value=1,
    max_value=10,
    value=5,
)

n_calls = st.sidebar.number_input(
    "Simulated calls",
    min_value=2000,
    max_value=100000,
    value=12000,
    step=1000,
)

run = st.sidebar.button("▶ Run Experiment", type="primary", use_container_width=True)

if "run_id" not in st.session_state:
    st.session_state.run_id = 0

if run:
    st.session_state.run_id += 1

    cfg = ExperimentConfig(
        experiment_id=f"vani-demo-{st.session_state.run_id}",
        name=f"Prompt Experiment — {scenario_name}",
        control_prompt="Current VANI prompt",
        treatment_prompt="Candidate prompt v2",
        split_b=split_b,
        alpha=0.05 / max_looks,
        min_per_arm=int(min_per_arm),
        max_looks=int(max_looks),
    )

    df = simulate_calls(
        scenario,
        n=int(n_calls),
        split_b=split_b,
        experiment_id=cfg.experiment_id,
    )

    audit = AuditLog()
    audit.add("EXPERIMENT_CREATED", cfg.to_dict())

    rows = []
    for look_no, batch in enumerate(replay_in_batches(df, batch_size=max(500, int(n_calls // max_looks))), start=1):
        a = batch[batch.variant == "A"]
        b = batch[batch.variant == "B"]

        # Cumulative data up to this look.
        current = df.iloc[: min(look_no * len(batch), len(df))]
        a_all = current[current.variant == "A"]
        b_all = current[current.variant == "B"]

        d = decide(
            int(a_all.meeting_fixed.sum()),
            len(a_all),
            int(b_all.meeting_fixed.sum()),
            len(b_all),
            alpha=cfg.alpha,
            min_per_arm=cfg.min_per_arm,
        )

        rows.append(
            {
                "look": look_no,
                "a_n": len(a_all),
                "b_n": len(b_all),
                "a_rate": d.a_rate,
                "b_rate": d.b_rate,
                "lift": d.lift,
                "p_value": d.p_value,
                "ci_low": d.ci_low,
                "ci_high": d.ci_high,
                "decision": d.status,
            }
        )

        if d.status in {"WIN", "STOP"}:
            audit.add(
                "DECISION",
                {
                    "look": look_no,
                    "status": d.status,
                    "p_value": d.p_value,
                    "lift": d.lift,
                    "reason": d.reason,
                },
            )
            break

    look_df = pd.DataFrame(rows)
    final = look_df.iloc[-1]

    # Store.
    st.session_state.cfg = cfg
    st.session_state.df = df
    st.session_state.look_df = look_df
    st.session_state.final = final
    st.session_state.audit = audit
    st.session_state.scenario = scenario

# ---------- Main ----------
if "df" not in st.session_state:
    st.info("Choose a scenario and click **Run Experiment** to generate a judge-ready demonstration.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("B wins", "PROMOTE", "positive evidence")
    with c2:
        st.metric("B worse", "STOP", "protect traffic")
    with c3:
        st.metric("Weak evidence", "INCONCLUSIVE", "don't ship blindly")

    st.markdown("### What this demo proves")
    st.markdown(
        """
        **1. Sticky assignment** — a lead always sees the same variant in the experiment.

        **2. Statistical decision** — the system does not call a winner merely because B's point estimate is higher.

        **3. Safe rollout** — a clearly worse treatment is stopped and traffic returns to control.

        **4. Honest uncertainty** — insufficient evidence remains inconclusive.
        """
    )
    st.stop()

cfg = st.session_state.cfg
df = st.session_state.df
look_df = st.session_state.look_df
final = st.session_state.final
audit = st.session_state.audit

# ---------- Metrics ----------
a = df[df.variant == "A"]
b = df[df.variant == "B"]

a_rate = a.meeting_fixed.mean()
b_rate = b.meeting_fixed.mean()
actual_b = len(b) / len(df)

d = decide(
    int(a.meeting_fixed.sum()),
    len(a),
    int(b.meeting_fixed.sum()),
    len(b),
    alpha=cfg.alpha,
    min_per_arm=cfg.min_per_arm,
)

decision = d.status
decision_label = {
    "WIN": "🚀 PROMOTE B",
    "STOP": "🛑 STOP B",
    "INCONCLUSIVE": "⏳ INCONCLUSIVE",
}[decision]

cols = st.columns(5)
cols[0].metric("A — Meeting Fixed", f"{a_rate:.2%}", f"{len(a):,} calls")
cols[1].metric("B — Meeting Fixed", f"{b_rate:.2%}", f"{len(b):,} calls")
cols[2].metric("Relative Lift", f"{d.lift:+.1%}")
cols[3].metric("p-value", f"{d.p_value:.4f}")
cols[4].metric("B Traffic", f"{actual_b:.1%}", f"target {split_b:.1%}")

if decision == "WIN":
    box = "background:#ecfdf5;color:#065f46;"
elif decision == "STOP":
    box = "background:#fef2f2;color:#991b1b;"
else:
    box = "background:#fffbeb;color:#92400e;"

st.markdown(
    f'<div class="decision" style="{box}">{decision_label} — {d.reason}</div>',
    unsafe_allow_html=True,
)

# ---------- Tabs ----------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Experiment", "📈 Statistical Evidence", "🔐 Assignment & Split", "🧾 Audit Log"]
)

with tab1:
    st.subheader("Experiment overview")

    left, right = st.columns([1.4, 1])

    with left:
        fig = go.Figure(
            data=[
                go.Bar(
                    x=["Control A", "Treatment B"],
                    y=[a_rate * 100, b_rate * 100],
                    text=[f"{a_rate:.2%}", f"{b_rate:.2%}"],
                    textposition="auto",
                )
            ]
        )
        fig.update_layout(
            title="Primary metric — Meeting Fixed Rate",
            yaxis_title="Rate (%)",
            yaxis_range=[0, max(a_rate, b_rate) * 100 * 1.35],
            height=380,
            margin=dict(l=20, r=20, t=60, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Experiment configuration")
        st.json(
            {
                "experiment_id": cfg.experiment_id,
                "control": cfg.control_prompt,
                "treatment": cfg.treatment_prompt,
                "configured_B_split": f"{cfg.split_b:.1%}",
                "achieved_B_split": f"{actual_b:.1%}",
                "primary_metric": cfg.primary_metric,
                "secondary_metric": cfg.secondary_metric,
                "per-look_alpha": cfg.alpha,
                "minimum_per_arm": cfg.min_per_arm,
                "planned_looks": cfg.max_looks,
            }
        )

    st.subheader("Secondary metric — Call Duration")

    duration_df = (
        df.groupby("variant")["call_duration_sec"]
        .agg(["mean", "median", "count"])
        .reset_index()
    )
    duration_df["variant"] = duration_df["variant"].map(
        {"A": "Control A", "B": "Treatment B"}
    )
    st.dataframe(duration_df, use_container_width=True, hide_index=True)

    st.caption(
        "Primary metric decides. Call duration is displayed as a secondary/guardrail metric, "
        "matching the problem statement's primary-vs-secondary framing."
    )

with tab2:
    st.subheader("Statistical evidence")

    st.markdown(
        f"""
        **Decision policy**

        - Family-wise alpha: **0.05**
        - Planned looks: **{cfg.max_looks}**
        - Per-look alpha: **{cfg.alpha:.3f}**
        - Minimum sample: **{cfg.min_per_arm:,} per arm**
        - Method: **two-proportion z-test**
        - Winner requires positive CI + statistical significance.
        - Worse treatment requires negative CI + statistical significance.
        """
    )

    st.markdown("#### Cumulative decision path")

    display = look_df.copy()
    display["a_rate"] = display["a_rate"].map(lambda x: f"{x:.2%}")
    display["b_rate"] = display["b_rate"].map(lambda x: f"{x:.2%}")
    display["lift"] = display["lift"].map(lambda x: f"{x:+.1%}")
    display["p_value"] = display["p_value"].map(lambda x: f"{x:.5f}")
    display["ci_low"] = display["ci_low"].map(
        lambda x: "—" if x == float("-inf") else f"{x:+.2%}"
    )
    display["ci_high"] = display["ci_high"].map(
        lambda x: "—" if x == float("inf") else f"{x:+.2%}"
    )
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("#### Confidence interval for B − A")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[0],
            y=[d.diff * 100],
            mode="markers",
            name="Observed difference",
        )
    )
    if d.ci_low != float("-inf") and d.ci_high != float("inf"):
        fig.add_trace(
            go.Scatter(
                x=[0, 0],
                y=[d.ci_low * 100, d.ci_high * 100],
                mode="lines",
                name="95% CI",
            )
        )
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(
        yaxis_title="B − A (percentage points)",
        xaxis=dict(showticklabels=False),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "Repeated checks are handled conservatively with a pre-declared Bonferroni correction. "
        "This makes the demo easy to defend: we do not repeatedly peek at raw p < 0.05 and "
        "declare victory."
    )

with tab3:
    st.subheader("Random + sticky assignment")

    st.markdown(
        """
        Assignment uses:

        `SHA256(experiment_id + lead_id) → deterministic bucket → A/B`

        Therefore:
        - assignment looks random across many leads;
        - the same lead stays on the same variant during the experiment;
        - no mutable session state is required for the basic assignment.
        """
    )

    sample_ids = ["L0000001", "L0000042", "L0001000", "L0099999"]
    rows = []
    for lead in sample_ids:
        v1 = assign_variant(lead, cfg.experiment_id, cfg.split_b)
        v2 = assign_variant(lead, cfg.experiment_id, cfg.split_b)
        rows.append({"lead_id": lead, "first_assignment": v1, "repeat_assignment": v2, "sticky": v1 == v2})

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    split = pd.Series(df.variant).value_counts().rename(index={"A": "Control A", "B": "Treatment B"})
    fig = go.Figure(
        data=[
            go.Pie(
                labels=split.index,
                values=split.values,
                hole=0.55,
                textinfo="label+percent",
            )
        ]
    )
    fig.update_layout(title="Achieved traffic split", height=380)
    st.plotly_chart(fig, use_container_width=True)

    st.success(
        f"Configured B = {cfg.split_b:.1%} | Achieved B = {actual_b:.1%} | "
        f"Absolute split error = {abs(actual_b-cfg.split_b):.2%}"
    )

with tab4:
    st.subheader("Decision audit trail")
    for event in audit.events:
        with st.expander(f"{event['timestamp']} — {event['event']}"):
            st.json(event["details"])

    st.download_button(
        "Download audit log",
        data=audit.as_json(),
        file_name="experiment_audit_log.json",
        mime="application/json",
    )

# ---------- Footer ----------
st.divider()
st.caption(
    "VANI Experiment Center • Hackathon demo implementation • "
    "Simulation/replay results are illustrative and must be labeled as such."
)
