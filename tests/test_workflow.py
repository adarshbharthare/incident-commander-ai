from backend.workflow import incident_graph


def test_database_incident_returns_evidence_and_runbook():
    result = incident_graph.invoke({
        "title": "Checkout failures",
        "service": "checkout-api",
        "environment": "production",
        "alert_description": "5xx errors above 8% for 10 minutes",
        "logs": "ERROR database connection pool exhausted\nERROR database timeout",
    })
    assert result["severity"] == "SEV-2"
    assert result["hypotheses"][0]["confidence"] >= 55
    assert result["runbooks"][0]["id"] == "RB-DB-001"
    assert "postmortem_draft" in result
