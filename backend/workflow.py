"""LangGraph workflow for explainable incident triage."""
from __future__ import annotations

import re
import uuid
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from backend.services import load_runbooks


class IncidentState(TypedDict, total=False):
    title: str
    service: str
    environment: str
    alert_description: str
    logs: str
    incident_id: str
    severity: str
    severity_reason: str
    log_evidence: list[str]
    hypotheses: list[dict]
    runbooks: list[dict]
    recommended_actions: list[str]
    stakeholder_update: str
    postmortem_draft: str
    trace: list[str]


SIGNATURES = {
    "database connection pool exhaustion": ["connection pool", "pool exhausted", "too many connections", "db timeout"],
    "upstream dependency degradation": ["upstream", "gateway timeout", "502", "503", "rate limit"],
    "container memory pressure or crash loop": ["oomkilled", "crashloopbackoff", "out of memory", "container restart"],
    "application exception spike": ["traceback", "unhandled exception", "nullpointerexception", "panic"],
}


def add_trace(state: IncidentState, name: str) -> list[str]:
    return [*state.get("trace", []), name]


def parse_alert(state: IncidentState) -> IncidentState:
    return {"incident_id": f"INC-{uuid.uuid4().hex[:8].upper()}", "trace": add_trace(state, "parsed alert")}


def classify_severity(state: IncidentState) -> IncidentState:
    text = f"{state['title']} {state['alert_description']} {state['logs']}".lower()
    if any(token in text for token in ["outage", "100%", "all users", "payment", "data loss"]):
        severity, reason = "SEV-1", "Potential broad customer impact or critical transaction failure was detected."
    elif any(token in text for token in ["5xx", "error rate", "degraded", "timeout", "8%"]):
        severity, reason = "SEV-2", "Elevated errors or degradation may affect a meaningful subset of users."
    elif any(token in text for token in ["warning", "latency", "slow"]):
        severity, reason = "SEV-3", "The alert indicates degradation without confirmed widespread failure."
    else:
        severity, reason = "SEV-4", "Insufficient indicators of current customer impact; continue monitoring."
    return {"severity": severity, "severity_reason": reason, "trace": add_trace(state, "classified severity")}


def extract_evidence(state: IncidentState) -> IncidentState:
    lines = [line.strip() for line in state["logs"].splitlines() if line.strip()]
    relevant = [line for line in lines if re.search(r"error|exception|timeout|fail|503|502|oom|pool", line, re.I)]
    return {"log_evidence": (relevant or lines)[:5], "trace": add_trace(state, "extracted log evidence")}


def analyze_root_cause(state: IncidentState) -> IncidentState:
    text = f"{state['alert_description']} {state['logs']}".lower()
    hypotheses = []
    for cause, keywords in SIGNATURES.items():
        matches = [word for word in keywords if word in text]
        if matches:
            evidence = [
                {"source": "alert", "detail": state["alert_description"][:240]},
                *[{"source": "log", "detail": line[:240]} for line in state["log_evidence"][:2]],
            ]
            hypotheses.append({"cause": cause.title(), "confidence": min(92, 55 + 12 * len(matches)), "evidence": evidence})
    if not hypotheses:
        hypotheses = [{"cause": "Insufficient correlated evidence; investigate recent changes and dependency health.", "confidence": 35, "evidence": [{"source": "alert", "detail": state["alert_description"][:240]}]}]
    return {"hypotheses": sorted(hypotheses, key=lambda x: x["confidence"], reverse=True)[:3], "trace": add_trace(state, "generated root-cause hypotheses")}


def retrieve_runbooks(state: IncidentState) -> IncidentState:
    corpus = f"{state['alert_description']} {state['logs']} {' '.join(h['cause'] for h in state['hypotheses'])}".lower()
    matches = []
    for runbook in load_runbooks():
        score = sum(keyword in corpus for keyword in runbook["keywords"])
        if score:
            matches.append({**runbook, "relevance": min(100, score * 30 + 25)})
    return {"runbooks": sorted(matches, key=lambda item: item["relevance"], reverse=True)[:3], "trace": add_trace(state, "retrieved runbooks")}


def recommend_actions(state: IncidentState) -> IncidentState:
    actions = ["Assign an incident commander and verify customer impact.", "Capture dashboards, deployment history, and affected request samples."]
    if state["runbooks"]:
        actions.extend(state["runbooks"][0]["steps"][:2])
    else:
        actions.append("Compare error timing with recent deployments and dependency status pages.")
    actions.append("Do not run remediation commands without an explicit human approval gate.")
    return {"recommended_actions": actions, "trace": add_trace(state, "planned recommended actions")}


def compose_outputs(state: IncidentState) -> IncidentState:
    top = state["hypotheses"][0]
    update = (f"[{state['severity']}] Investigating {state['title']} in {state['environment']}. "
              f"Current leading hypothesis: {top['cause']} ({top['confidence']}% confidence). "
              "The team is validating impact and following the relevant runbook. Next update in 15 minutes.")
    postmortem = f"""# Postmortem Draft: {state['title']}

## Incident
{state['incident_id']} — {state['severity']} — {state['service']} ({state['environment']})

## Summary
{state['severity_reason']}

## Leading hypothesis
{top['cause']} ({top['confidence']}% confidence)

## Evidence
""" + "\n".join(f"- {item['detail']}" for item in top["evidence"]) + "\n\n## Follow-up actions\n" + "\n".join(f"- [ ] {action}" for action in state["recommended_actions"])
    return {"stakeholder_update": update, "postmortem_draft": postmortem, "trace": add_trace(state, "composed incident outputs")}


def build_graph():
    graph = StateGraph(IncidentState)
    graph.add_node("parse_alert", parse_alert)
    graph.add_node("classify_severity", classify_severity)
    graph.add_node("extract_evidence", extract_evidence)
    graph.add_node("analyze_root_cause", analyze_root_cause)
    graph.add_node("retrieve_runbooks", retrieve_runbooks)
    graph.add_node("recommend_actions", recommend_actions)
    graph.add_node("compose_outputs", compose_outputs)
    graph.add_edge(START, "parse_alert")
    graph.add_edge("parse_alert", "classify_severity")
    graph.add_edge("classify_severity", "extract_evidence")
    graph.add_edge("extract_evidence", "analyze_root_cause")
    graph.add_edge("analyze_root_cause", "retrieve_runbooks")
    graph.add_edge("retrieve_runbooks", "recommend_actions")
    graph.add_edge("recommend_actions", "compose_outputs")
    graph.add_edge("compose_outputs", END)
    return graph.compile()


incident_graph = build_graph()
