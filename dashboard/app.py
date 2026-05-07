"""Streamlit dashboard for Traceset — shows traces with confidence scores."""

import httpx
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Traceset", layout="wide")
st.title("Traceset — Intelligence Engine")

# ─── Sidebar: Input form ──────────────────────────────────────────────────────

with st.sidebar:
    st.header("Sentinel Controls")

    repo = st.text_input("GitHub Repo (owner/name)", placeholder="openai/triton")
    authors_raw = st.text_area(
        "Author names (one per line)",
        placeholder="Tri Dao\nTim Dettmers",
    )
    cpc_class = st.text_input("CPC Patent Class (optional)", placeholder="G06N3/04")
    assignee = st.text_input("Patent Assignee (optional)", placeholder="Meta Platforms")

    run = st.button("Run Sentinels", type="primary")

# ─── Run sentinels ────────────────────────────────────────────────────────────

if run:
    author_list = [a.strip() for a in authors_raw.splitlines() if a.strip()]

    with st.spinner("Fetching commits..."):
        if repo:
            try:
                r = httpx.post(f"{API_BASE}/commits/watch", params={"repo": repo}, timeout=60)
                r.raise_for_status()
                st.success(f"Stored {len(r.json())} commits from {repo}")
            except Exception as exc:
                st.error(f"Commit fetch failed: {exc}")

    with st.spinner("Syncing papers..."):
        if author_list:
            try:
                r = httpx.post(
                    f"{API_BASE}/papers/sync",
                    params={"authors": author_list},
                    timeout=60,
                )
                r.raise_for_status()
                st.success(f"Stored {len(r.json())} papers")
            except Exception as exc:
                st.error(f"Paper sync failed: {exc}")

    with st.spinner("Searching patents..."):
        if assignee or cpc_class:
            try:
                params: dict = {}
                if assignee:
                    params["assignee"] = assignee
                if cpc_class:
                    params["cpc_class"] = cpc_class
                r = httpx.post(f"{API_BASE}/patents/search", params=params, timeout=60)
                r.raise_for_status()
                st.success(f"Stored {len(r.json())} patents")
            except Exception as exc:
                st.error(f"Patent search failed: {exc}")

# ─── Traces table ─────────────────────────────────────────────────────────────

st.divider()
st.subheader("Trace Results")

min_conf = st.slider("Minimum confidence score", 0.0, 1.0, 0.3, 0.05)

try:
    resp = httpx.get(
        f"{API_BASE}/traces/",
        params={"min_confidence": min_conf, "limit": 100},
        timeout=10,
    )
    resp.raise_for_status()
    traces = resp.json()
except Exception as exc:
    st.warning(f"Could not load traces: {exc}")
    traces = []

if not traces:
    st.info("No traces found. Run the sentinels and then use POST /traces/analyze to link pairs.")
else:
    for trace in traces:
        conf = trace.get("confidence_score", 0.0)
        color = "green" if conf >= 0.7 else "orange" if conf >= 0.4 else "red"
        with st.expander(
            f":{color}[{conf:.0%}] — {trace.get('trace_type', '').replace('_', ' ').title()}"
        ):
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("Confidence", f"{conf:.0%}")
                st.caption(f"Model: {trace.get('model_version', 'N/A')}")
                st.caption(f"Prompt v{trace.get('prompt_version', 1)}")
            with col2:
                st.markdown("**Reasoning**")
                st.write(trace.get("reasoning", ""))
            st.caption(
                f"Trace ID: {trace.get('id', 'N/A')} | "
                f"Created: {trace.get('created_at', '')[:19]}"
            )
