"""Configuration management for Mjolnir.

Reads settings from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class MjolnirConfig:
    """Central configuration object.

    All values fall back to environment variables prefixed with
    ``MJOLNIR_``, then to hard-coded defaults.
    """
    dashboard_name: str = ""
    refresh_interval: int = 5
    max_metric_history: int = 10_000
    alert_check_interval: int = 10
    log_level: str = "INFO"
    context_limit: int = 200_000
    extra: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.dashboard_name = self.dashboard_name or os.getenv(
            "MJOLNIR_DASHBOARD_NAME", "mjolnir"
        )
        self.refresh_interval = int(
            os.getenv("MJOLNIR_REFRESH_INTERVAL", str(self.refresh_interval))
        )
        self.max_metric_history = int(
            os.getenv("MJOLNIR_MAX_HISTORY", str(self.max_metric_history))
        )
        self.log_level = os.getenv("MJOLNIR_LOG_LEVEL", self.log_level)

    def to_dict(self) -> Dict[str, object]:
        return {
            "dashboard_name": self.dashboard_name,
            "refresh_interval": self.refresh_interval,
            "max_metric_history": self.max_metric_history,
            "alert_check_interval": self.alert_check_interval,
            "log_level": self.log_level,
            "context_limit": self.context_limit,
        }
