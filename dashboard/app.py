"""Traceset dashboard — 5-agent competitive intelligence pipeline."""

import threading
import time

import streamlit as st

from orchestrator import PipelineStatus, run_pipeline

st.set_page_config(page_title="Traceset", layout="wide", page_icon="🔍")

st.title("Traceset — Competitive Intelligence Engine")
st.caption("Enter a company name. Five AI agents will research it, find competitors, monitor their activity, and report back.")

# ─── Input ────────────────────────────────────────────────────────────────────

col1, col2 = st.columns([3, 1])
with col1:
    company = st.text_input("Company to analyze", placeholder="e.g. OpenAI, Stripe, Notion")
with col2:
    lookback = st.selectbox("Lookback window", [30, 90, 180, 365], index=2, format_func=lambda x: f"{x} days")

with st.expander("Advanced settings"):
    min_conf = st.slider("Minimum trace confidence", 0.0, 1.0, 0.4, 0.05)
    max_pairs = st.number_input("Max commit×paper pairs to analyze", 5, 50, 20)

run_btn = st.button("Run Analysis", type="primary", disabled=not company.strip())

# ─── Agent progress display ───────────────────────────────────────────────────

AGENTS = [
    ("1", "Company Researcher", "Profiling the company — tech focus, key people, GitHub orgs"),
    ("2", "Competitor Mapper", "Identifying top 3–5 competitors and their digital footprints"),
    ("3", "Sentinel", "Collecting commits, papers, and patents in parallel"),
    ("4", "Trace Engine", "Linking code changes to research papers via Claude"),
    ("5", "Strategic Analyst", "Synthesizing everything into an intelligence report"),
]

DONE_FLAGS = [
    "agent_1_done", "agent_2_done", "agent_3_done", "agent_4_done", "agent_5_done"
]


def render_progress(status: PipelineStatus):
    for i, (num, name, desc) in enumerate(AGENTS):
        done = getattr(status, DONE_FLAGS[i], False)
        # which agent is currently running
        prev_done = getattr(status, DONE_FLAGS[i - 1], True) if i > 0 else True
        running = prev_done and not done and status.error is None

        if done:
            icon = "✅"
        elif running:
            icon = "⏳"
        else:
            icon = "⬜"

        st.markdown(f"{icon} **Agent {num}: {name}** — {desc}")


if run_btn and company.strip():
    st.divider()
    st.subheader(f"Analyzing: {company.strip()}")

    # Placeholders so we can update them in place
    progress_placeholder = st.empty()
    report_placeholder = st.empty()
    error_placeholder = st.empty()

    status_holder: dict = {"status": None}

    def _run():
        def _on_progress(s: PipelineStatus):
            status_holder["status"] = s

        run_pipeline(
            company_name=company.strip(),
            lookback_days=lookback,
            min_confidence=min_conf,
            max_pairs=int(max_pairs),
            on_progress=_on_progress,
            verbose=True,
        )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    # Poll until the thread finishes, updating UI each tick
    while thread.is_alive():
        s = status_holder["status"]
        if s:
            with progress_placeholder.container():
                render_progress(s)
        time.sleep(1)
        st.rerun()

    # Final render after thread completes
    s = status_holder["status"]
    if s is None:
        error_placeholder.error("Pipeline did not return a status. Check terminal logs.")
    elif s.error:
        with progress_placeholder.container():
            render_progress(s)
        error_placeholder.error(f"Pipeline failed: {s.error}")
    elif s.report:
        with progress_placeholder.container():
            render_progress(s)
        st.success("Analysis complete!")
        st.divider()
        report_placeholder.markdown(s.report.markdown)

        # Download button
        st.download_button(
            label="Download Report",
            data=s.report.markdown,
            file_name=f"traceset_{s.company.lower().replace(' ', '_')}.md",
            mime="text/markdown",
        )
