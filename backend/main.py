from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import IncidentRequest, IncidentResponse, RunbookMatch
from backend.services import load_runbooks
from backend.workflow import incident_graph

app = FastAPI(title="Incident Commander AI", version="1.0.0", description="Evidence-backed incident triage with LangGraph.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8501"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "incident-commander-ai"}


@app.get("/api/v1/runbooks", response_model=list[RunbookMatch])
def runbooks():
    return [{**item, "relevance": 0} for item in load_runbooks()]


@app.post("/api/v1/incidents/analyze", response_model=IncidentResponse)
def analyze_incident(request: IncidentRequest):
    result = incident_graph.invoke(request.model_dump())
    return {**result, "status": "Investigating"}
