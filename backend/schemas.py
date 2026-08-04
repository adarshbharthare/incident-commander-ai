from typing import Literal

from pydantic import BaseModel, Field


class IncidentRequest(BaseModel):
    title: str = Field(..., min_length=4, examples=["Checkout API error rate spike"])
    service: str = Field(..., examples=["checkout-api"])
    environment: str = Field(default="production")
    alert_description: str = Field(..., min_length=10)
    logs: str = Field(..., min_length=10)


class Evidence(BaseModel):
    source: Literal["alert", "log", "runbook"]
    detail: str


class Hypothesis(BaseModel):
    cause: str
    confidence: int = Field(ge=0, le=100)
    evidence: list[Evidence]


class RunbookMatch(BaseModel):
    id: str
    title: str
    owner: str
    relevance: int
    steps: list[str]


class IncidentResponse(BaseModel):
    incident_id: str
    severity: Literal["SEV-1", "SEV-2", "SEV-3", "SEV-4"]
    severity_reason: str
    status: str
    hypotheses: list[Hypothesis]
    runbooks: list[RunbookMatch]
    recommended_actions: list[str]
    stakeholder_update: str
    postmortem_draft: str
    trace: list[str]
