"""Scoring weights and thresholds.

Read from the ``engine_config`` table so the Ministry threshold screen can retune
them, falling back to ``config/weights.yaml`` when the table is empty. The file
stays as the documented default and as the source the table is seeded from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import BACKEND_ROOT
from app.models.enums import ModuleCode, SeverityTier
from app.models.risk import EngineConfig

WEIGHTS_PATH = BACKEND_ROOT / "app" / "config" / "weights.yaml"


@lru_cache(maxsize=1)
def _file_defaults() -> dict:
    return yaml.safe_load(WEIGHTS_PATH.read_text(encoding="utf-8"))


@dataclass
class Config:
    engine_version: str
    stage1: dict[str, float]
    stage2: dict[str, float]
    stage3: dict[str, float]
    tiers: dict[str, float]
    thresholds: dict[str, float]
    caps: dict[str, float] = field(default_factory=dict)

    def weights_for(self, stage: str) -> dict[ModuleCode, float]:
        raw = {"STAGE_1": self.stage1, "STAGE_2": self.stage2, "STAGE_3": self.stage3}[stage]
        return {ModuleCode(k): v for k, v in raw.items()}

    def t(self, key: str) -> float:
        """A threshold by name. Missing keys are a programming error, not a default."""
        if key not in self.thresholds:
            raise KeyError(f"threshold {key!r} is not defined in weights.yaml")
        return self.thresholds[key]

    def tier_for(self, score: float) -> SeverityTier:
        if score >= self.tiers["CRITICAL_MIN"]:
            return SeverityTier.CRITICAL
        if score >= self.tiers["HIGH_MIN"]:
            return SeverityTier.HIGH
        if score >= self.tiers["MEDIUM_MIN"]:
            return SeverityTier.MEDIUM
        return SeverityTier.LOW


def load_config(db: Session | None = None) -> Config:
    """Database first, file second."""
    defaults = _file_defaults()
    cfg = Config(
        engine_version=defaults["engine_version"],
        stage1=dict(defaults["stage1"]),
        stage2=dict(defaults["stage2"]),
        stage3=dict(defaults["stage3"]),
        tiers=dict(defaults["tiers"]),
        thresholds=dict(defaults["thresholds"]),
        caps=dict(defaults.get("caps", {})),
    )

    if db is None:
        return cfg

    scopes = {
        "stage1": cfg.stage1,
        "stage2": cfg.stage2,
        "stage3": cfg.stage3,
        "tiers": cfg.tiers,
        "thresholds": cfg.thresholds,
        "caps": cfg.caps,
    }
    for row in db.scalars(select(EngineConfig)).all():
        target = scopes.get(row.scope)
        if target is not None:
            target[row.key] = row.value
    return cfg
