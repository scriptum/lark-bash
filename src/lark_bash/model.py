from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SourceSpan:
    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass(slots=True)
class HeredocRecord:
    delimiter: str
    quoted: bool
    body: str
    start_line: int
    end_line: int


@dataclass(slots=True)
class SubstitutionRecord:
    kind: str
    raw: str
    subtree: Any


@dataclass(slots=True)
class CommandRecord:
    name: str | None
    args: list[str]
    redirects: list[str]
    assignments: list[str]
    substitutions: list[SubstitutionRecord]
    heredocs: list[HeredocRecord]
    source_span: SourceSpan | None
    raw_node: Any
