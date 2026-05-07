"""Shared base class for all Traceset agents."""

import time
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentResult:
    agent_name: str
    success: bool
    duration_seconds: float
    error: str | None = None


class BaseAgent:
    name: str = "base"

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._start: float = 0.0

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[{self.name.upper()}] {msg}")

    def _start_timer(self) -> None:
        self._start = time.time()

    def _elapsed(self) -> float:
        return round(time.time() - self._start, 2)
