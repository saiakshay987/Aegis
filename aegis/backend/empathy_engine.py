"""
Aegis – Empathy/LLM Layer
Owner: Manieesh Manohar

Receives a distress JSON from the ML backend and returns a 2-sentence
empathetic response for the Customer Alert Modal.

Supports:
  - OpenAI  (gpt-4o-mini, default)
  - Gemini  (gemini-1.5-flash, fallback)

Deployment Modes
================
This module supports TWO deployment configurations:

1. **In-Process (Default)** — Imported as a library by
   ``aegis/backend/services/logic_service.py``.  No separate process is
   needed; ``logic_service`` calls ``build_prompt()``, ``call_openai()``,
   ``call_gemini()``, and ``get_fallback()`` directly.  This is the mode
   used by the demo and by the main FastAPI app (``main.py`` on port 8000).

2. **Standalone Microservice** — Run independently via:
       uvicorn empathy_engine:app --reload --port 8001
   Exposes a ``POST /generate`` endpoint that accepts a ``DistressPayload``
   JSON body and returns an empathetic message.  Useful for horizontal
   scaling or isolating LLM latency from the main API.

The in-process mode is recommended for development and single-server
deployments.  Switch to standalone mode only when you need to scale the
LLM layer independently or run it behind a separate load balancer.
"""


import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx

app = FastAPI(title="Aegis Empathy Engine", version="1.0.0")

# Allow the mobile UI (any origin during hackathon)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ── Config ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Request / Response schemas ────────────────────────────────────────────────

class DistressPayload(BaseModel):
    """
    Shape coming from Nihaal's ML backend.
    Example: {"shock": "medical", "amount": 35000, "user_name": "Arjun",
               "emi": 8000, "recommended_emi": 4500, "balance": 2000}
    """
    shock: str                          # "medical" | "job_loss" | "utility" | "other"
    amount: float                       # shock expense amount in INR
    user_name: Optional[str] = "User"
    balance: Optional[float] = None     # current account balance
    emi: Optional[float] = None         # current EMI
    recommended_emi: Optional[float] = None   # ML-suggested reduced EMI
    deferred_amount: Optional[float] = None   # amount that can be deferred interest-free

class EmpathyResponse(BaseModel):
    headline: str    # short bold line for the modal header
    message: str     # 2-sentence empathetic body
    suggestion: str  # one clear action line


# ── Prompt builder ─────────────────────────────────────────────────────────────

def build_prompt(payload: DistressPayload) -> str:
    """
    Constructs the LLM prompt following the Aegis rules:
      - Do NOT blame the user
      - Explain the shock in plain language
      - Suggest the adaptive repayment concretely
    """
    emi_line = ""
    if payload.emi and payload.recommended_emi:
        deferred = payload.deferred_amount or round(payload.emi - payload.recommended_emi, 2)
        emi_line = (
            f"The system recommends temporarily reducing their EMI from "
            f"₹{payload.emi:,.0f} to ₹{payload.recommended_emi:,.0f} this month, "
            f"deferring ₹{deferred:,.0f} interest-free."
        )

    balance_line = ""
    if payload.balance is not None:
        balance_line = f"Their current account balance is ₹{payload.balance:,.0f}."

    return f"""You are a compassionate financial wellness assistant for Aegis, a lending app.

A customer named {payload.user_name} has just experienced a financial shock.
Shock type: {payload.shock}
Shock amount: ₹{payload.amount:,.0f}
{balance_line}
{emi_line}

Write a response with EXACTLY this structure:
1. HEADLINE: A short (max 8 words), warm, non-judgmental headline. No exclamation marks.
2. MESSAGE: Exactly 2 sentences. First sentence acknowledges the shock without any blame — treat it as an unexpected life event. Second sentence explains simply why their finances are under stress right now.
3. SUGGESTION: One clear, specific action sentence telling them what Aegis will do to help (use the EMI/deferral numbers if provided).

Rules:
- Never use words like "poor decision", "overspent", "irresponsible", or any blame language.
- Be warm, human, and direct — no corporate jargon.
- Use Indian Rupee symbol ₹ for amounts.
- Output format (use these exact labels):
HEADLINE: <text>
MESSAGE: <text>
SUGGESTION: <text>"""


# ── LLM callers ───────────────────────────────────────────────────────────────

async def call_openai(prompt: str) -> dict:
    """Call OpenAI gpt-4o-mini."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 200,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def call_gemini(prompt: str) -> str:
    """Call Gemini 1.5 Flash as fallback."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def parse_llm_output(raw: str) -> EmpathyResponse:
    """Parse the structured HEADLINE / MESSAGE / SUGGESTION output."""
    lines = {
        k.strip(): v.strip()
        for line in raw.strip().splitlines()
        if ":" in line
        for k, v in [line.split(":", 1)]
    }
    return EmpathyResponse(
        headline=lines.get("HEADLINE", "We're here to help you through this."),
        message=lines.get("MESSAGE", raw[:300]),
        suggestion=lines.get("SUGGESTION", "Please contact our support team."),
    )


# ── Fallback (no API key available — safe for demo) ───────────────────────────

FALLBACK_RESPONSES = {
    "medical": EmpathyResponse(
        headline="You're navigating an unexpected medical storm.",
        message=(
            "A sudden hospital expense of ₹{amount:,.0f} hit your account — "
            "this is a life event, not a financial misstep. "
            "It has temporarily strained your cash flow and brought your balance to a critical level."
        ),
        suggestion=(
            "Aegis will reduce your EMI to ₹{recommended_emi:,.0f} this month, "
            "deferring ₹{deferred:,.0f} completely interest-free until you stabilise."
        ),
    ),
    "job_loss": EmpathyResponse(
        headline="Losing income is hard — we've got you.",
        message=(
            "An unexpected income gap of ₹{amount:,.0f} has put your finances under pressure — "
            "this happens to millions and it is not a reflection of your choices. "
            "Your balance is temporarily at a critical level."
        ),
        suggestion=(
            "Aegis will pause your EMI this month and defer ₹{deferred:,.0f} interest-free "
            "while you get back on your feet."
        ),
    ),
    "other": EmpathyResponse(
        headline="An unexpected expense hit your account.",
        message=(
            "A sudden expense of ₹{amount:,.0f} was recorded — unexpected costs like this "
            "can strain even the most careful plans. "
            "Your current balance reflects this temporary pressure."
        ),
        suggestion=(
            "Aegis can reduce your EMI temporarily and defer the difference "
            "interest-free to give you breathing room."
        ),
    ),
}

def get_fallback(payload: DistressPayload) -> EmpathyResponse:
    template = FALLBACK_RESPONSES.get(payload.shock, FALLBACK_RESPONSES["other"])
    deferred = payload.deferred_amount or (
        round(payload.emi - payload.recommended_emi, 2)
        if payload.emi and payload.recommended_emi else 0
    )
    fmt = dict(
        amount=payload.amount,
        recommended_emi=payload.recommended_emi or 0,
        deferred=deferred,
    )
    return EmpathyResponse(
        headline=template.headline,
        message=template.message.format(**fmt),
        suggestion=template.suggestion.format(**fmt),
    )


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.post("/empathy", response_model=EmpathyResponse)
async def generate_empathy(payload: DistressPayload):
    """
    Main endpoint called by Harris's mobile UI (via Nihaal's backend).
    POST /empathy
    Body: DistressPayload JSON
    Returns: EmpathyResponse JSON
    """
    prompt = build_prompt(payload)

    # Try OpenAI → Gemini → fallback (so demo always works)
    raw = None
    if OPENAI_API_KEY:
        try:
            raw = await call_openai(prompt)
        except Exception as e:
            print(f"[OpenAI failed] {e} – trying Gemini")

    if raw is None and GEMINI_API_KEY:
        try:
            raw = await call_gemini(prompt)
        except Exception as e:
            print(f"[Gemini failed] {e} – using fallback")

    if raw is None:
        # Safe demo fallback — no API key needed
        return get_fallback(payload)

    return parse_llm_output(raw)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "openai": bool(OPENAI_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
    }


# ── Quick local test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio

    test_payload = DistressPayload(
        shock="medical",
        amount=35000,
        user_name="Arjun",
        balance=2000,
        emi=8000,
        recommended_emi=4500,
        deferred_amount=3500,
    )

    async def run():
        result = await generate_empathy(test_payload)
        print("\n── Empathy Response ──────────────────────")
        print(f"HEADLINE:   {result.headline}")
        print(f"MESSAGE:    {result.message}")
        print(f"SUGGESTION: {result.suggestion}")

    asyncio.run(run())
