import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
DATA_PATH = Path(__file__).parent / "data" / "runbooks.json"


def load_runbooks() -> list[dict]:
    return json.loads(DATA_PATH.read_text())


def get_llm_response(prompt: str) -> str | None:
    """Return a short optional LLM response; failures deliberately fall back to local logic."""
    provider = os.getenv("LLM_PROVIDER", "demo").lower()
    try:
        if provider == "openai" and os.getenv("OPENAI_API_KEY"):
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0).invoke(prompt).content
        if provider == "groq" and os.getenv("GROQ_API_KEY"):
            from langchain_groq import ChatGroq
            return ChatGroq(model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"), temperature=0).invoke(prompt).content
    except Exception:
        return None
    return None
