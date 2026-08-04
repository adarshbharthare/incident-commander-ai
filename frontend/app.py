import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

DEMO_LOGS = """2026-08-04T10:02:14Z ERROR checkout-api database connection pool exhausted; active=50 max=50
2026-08-04T10:02:17Z ERROR checkout-api request failed: database timeout after 3000ms
2026-08-04T10:03:02Z WARN checkout-api 5xx rate=9.4% route=/v1/checkout
2026-08-04T10:03:10Z INFO checkout-api deployment=2026.08.04-rc3"""

st.set_page_config(page_title="Incident Commander AI", page_icon="🚨", layout="wide")
st.title("🚨 Incident Commander AI")
st.caption("Evidence-backed incident triage powered by a LangGraph workflow.")

with st.sidebar:
    st.subheader("Workflow")
    st.markdown("Alert → Severity → Evidence → Root cause → Runbooks → Actions → Postmortem")
    st.caption(f"API: {API_URL}")

with st.form("incident_form"):
    left, right = st.columns(2)
    with left:
        title = st.text_input("Incident title", "Checkout API error rate spike")
        service = st.text_input("Service", "checkout-api")
    with right:
        environment = st.selectbox("Environment", ["production", "staging", "development"])
        alert = st.text_area("Alert description", "5xx rate is above 8% for 10 minutes. Customers cannot reliably complete checkout.", height=108)
    logs = st.text_area("Logs", DEMO_LOGS, height=200)
    submitted = st.form_submit_button("Analyze incident", type="primary", use_container_width=True)

if submitted:
    payload = {"title": title, "service": service, "environment": environment, "alert_description": alert, "logs": logs}
    try:
        with st.spinner("Running the incident workflow..."):
            response = requests.post(f"{API_URL}/api/v1/incidents/analyze", json=payload, timeout=45)
            response.raise_for_status()
            result = response.json()
    except requests.RequestException as exc:
        st.error(f"Could not reach the API. Start FastAPI first. Details: {exc}")
        st.stop()

    severity_color = {"SEV-1": "🔴", "SEV-2": "🟠", "SEV-3": "🟡", "SEV-4": "🔵"}
    st.success(f"{result['incident_id']} · {result['status']}")
    a, b, c = st.columns(3)
    a.metric("Severity", f"{severity_color[result['severity']]} {result['severity']}")
    b.metric("Top hypothesis", f"{result['hypotheses'][0]['confidence']}%")
    c.metric("Runbooks matched", len(result["runbooks"]))
    st.info(result["severity_reason"])

    tabs = st.tabs(["Root cause", "Runbooks & actions", "Stakeholder update", "Postmortem", "Workflow trace"])
    with tabs[0]:
        for hypothesis in result["hypotheses"]:
            st.subheader(f"{hypothesis['cause']} — {hypothesis['confidence']}%")
            for evidence in hypothesis["evidence"]:
                st.caption(f"{evidence['source'].upper()}: {evidence['detail']}")
    with tabs[1]:
        for runbook in result["runbooks"]:
            with st.expander(f"{runbook['id']} · {runbook['title']} ({runbook['relevance']}% match)"):
                st.caption(f"Owner: {runbook['owner']}")
                st.markdown("\n".join(f"- {step}" for step in runbook["steps"]))
        st.subheader("Recommended actions")
        st.markdown("\n".join(f"- {action}" for action in result["recommended_actions"]))
    with tabs[2]:
        st.code(result["stakeholder_update"], language=None)
    with tabs[3]:
        st.markdown(result["postmortem_draft"])
        st.download_button("Download postmortem", result["postmortem_draft"], file_name=f"{result['incident_id']}-postmortem.md")
    with tabs[4]:
        st.markdown("\n".join(f"{i + 1}. {step}" for i, step in enumerate(result["trace"])))
