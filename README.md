# Incident Commander AI

An agentic incident-triage workspace for SRE and platform teams. It transforms an alert and noisy logs into a severity assessment, evidence-backed root-cause hypotheses, relevant runbook steps, a stakeholder update, and a postmortem draft.

## What it demonstrates

- **LangGraph orchestration:** a visible, deterministic incident workflow.
- **LLM augmentation:** works with OpenAI or Groq, with a dependable local demo mode.
- **Evidence first:** every hypothesis links to the log lines and runbooks that motivated it.
- **Product thinking:** a FastAPI service plus a Streamlit operator dashboard.

## Architecture

```text
Alert + logs
     |
     v
Parse alert -> classify severity -> extract log evidence
     |                                  |
     +--------> retrieve runbooks <-----+
                         |
                         v
                root-cause analysis
                         |
                         v
       incident summary + postmortem draft + actions
```

## Run locally

Requires Python 3.10+.

```bash
cd incident-commander-ai
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env

# Terminal 1
uvicorn backend.main:app --reload --port 8000

# Terminal 2
streamlit run frontend/app.py
```

Open Streamlit at `http://localhost:8501`. It runs in **demo mode** until you add a provider and API key to `.env`.

## API

`POST /api/v1/incidents/analyze`

```json
{
  "title": "Checkout API error rate spike",
  "service": "checkout-api",
  "environment": "production",
  "alert_description": "5xx rate is above 8% for 10 minutes.",
  "logs": "ERROR database connection pool exhausted"
}
```

Useful endpoints: `/docs`, `/health`, and `/api/v1/runbooks`.

## Configure an LLM (optional)

Set `LLM_PROVIDER=openai` with `OPENAI_API_KEY`, or `LLM_PROVIDER=groq` with `GROQ_API_KEY`. The graph always has rule-based fallbacks, so API outages do not break the demo.

## Next steps

Replace the local runbook retriever with ChromaDB/FAISS, add Slack and PagerDuty adapters through MCP, persist incidents, then place approval gates in front of remediation actions.
