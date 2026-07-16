"""
model_config.py — THE one Groq model switch for VibeJobHunter / CMO (July 15 2026).

Models are rented, not owned: providers retire them every few months. Groq drops
llama-3.3-70b-versatile (dev tier) in August 2026, and llama-3.1-8b-instant is
decommissioned Aug 16 2026 — we already migrated off that one in June. Code should
never hard-code a model id, or every retirement means hunting strings across the repo.

Every Groq call site in VJH resolves its model id through groq_model(). Cutover is one
line in .env (GROQ_MODEL=...) plus a restart, and it is instantly reversible.

Matches the fleet-wide GROQ_MODEL switch in cto-aipa (src/llm-resilience.ts groqModel()).

Reads os.environ first, then falls back to the repo .env file — same defensive pattern as
llm_judge._key(), because the bot does not always load .env into os.environ and a silent
miss here would leave us pinned to a dead model.
"""

import os

_DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def groq_model() -> str:
    """Resolve the Groq model id: GROQ_MODEL env → repo .env → current default."""
    v = os.environ.get("GROQ_MODEL", "").strip()
    if v:
        return v
    try:
        from dotenv import dotenv_values
        from pathlib import Path

        v = (dotenv_values(Path(__file__).resolve().parents[2] / ".env").get("GROQ_MODEL") or "").strip()
    except Exception:
        v = ""
    return v or _DEFAULT_GROQ_MODEL
