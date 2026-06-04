"""Central configuration: model selection per role, paths, and loop caps.

All values are overridable through environment variables (see .env.example) so the
system can run on whatever local Ollama models are available, or fall back to a single
model to conserve memory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# Each graph node ("task role") is mapped to a model "tier". "coder" needs strong code
# + tool calling; "narrative" handles planning / design / ops prose. Unknown keys fall
# back to the narrative tier.
ROLE_TIERS: dict[str, str] = {
    "product_manager": "narrative",
    "ux_designer": "narrative",
    "tech_lead_design": "coder",
    "tech_lead_review": "coder",
    "qa_planning": "narrative",
    "software_engineer": "coder",
    "software_engineer_fix": "coder",
    "devops_ci": "narrative",
    "devops_cd": "narrative",
    "operate": "narrative",
}


@dataclass
class Settings:
    ollama_host: str = field(default_factory=lambda: _env("OLLAMA_HOST", "http://localhost:11434"))
    coder_model: str = field(default_factory=lambda: _env("SWTEAM_CODER_MODEL", "qwen2.5-coder:7b"))
    narrative_model: str = field(
        default_factory=lambda: _env("SWTEAM_NARRATIVE_MODEL", "llama3.1:8b")
    )
    temperature: float = field(default_factory=lambda: _env_float("SWTEAM_TEMPERATURE", 0.2))
    max_review_iters: int = field(default_factory=lambda: _env_int("SWTEAM_MAX_REVIEW_ITERS", 2))
    max_fix_iters: int = field(default_factory=lambda: _env_int("SWTEAM_MAX_FIX_ITERS", 2))

    def model_for(self, role: str) -> str:
        tier = ROLE_TIERS.get(role, "narrative")
        return self.coder_model if tier == "coder" else self.narrative_model


def repo_root() -> Path:
    # src/software_team/config.py -> repo root is three parents up.
    return Path(__file__).resolve().parents[2]


SETTINGS = Settings()
