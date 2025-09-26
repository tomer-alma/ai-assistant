from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BargeInConfig:
    stop_phrase: str
    energy_threshold: float = 0.02  # placeholder for future energy-based barge-in


class BargeIn:
    def __init__(self, config: BargeInConfig) -> None:
        self._config = config

    def should_interrupt(self, partial_text: str) -> bool:
        return self._config.stop_phrase in (partial_text or "")

