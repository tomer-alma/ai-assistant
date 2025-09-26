from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Turn:
    user: str
    assistant: str


@dataclass
class Session:
    history: List[Turn] = field(default_factory=list)
    max_turns: int = 8

    def add(self, user: str, assistant: str) -> None:
        self.history.append(Turn(user=user, assistant=assistant))
        if len(self.history) > self.max_turns:
            self.history = self.history[-self.max_turns :]

