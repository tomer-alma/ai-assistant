from __future__ import annotations

from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()


class FSM:
    def __init__(self) -> None:
        self.state = State.IDLE

    def to_idle(self) -> None:
        self.state = State.IDLE

    def to_listening(self) -> None:
        self.state = State.LISTENING

    def to_thinking(self) -> None:
        self.state = State.THINKING

    def to_speaking(self) -> None:
        self.state = State.SPEAKING

