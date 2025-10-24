"""Shared dataclasses and helpers for TLE core functionality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TLE:
    """Representation of a parsed two-line element set."""

    norad_id: str
    name: Optional[str]
    line1: str
    line2: str
    source: str

    def as_text(self, three_line: bool = True) -> str:
        if three_line and self.name:
            return f"{self.name}\n{self.line1}\n{self.line2}\n"
        return f"{self.line1}\n{self.line2}\n"


__all__ = ["TLE"]
