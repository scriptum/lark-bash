from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(slots=True)
class SourceSpan:
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    end_column: int | None = None


@dataclass(slots=True)
class Node:
    span: SourceSpan = field(default_factory=SourceSpan, kw_only=True)


@dataclass(slots=True)
class Script(Node):
    statements: list[Statement] = field(default_factory=list)
    here_docs: list[HereDoc] = field(default_factory=list)

    def iter_commands(self) -> Iterable[Command]:
        for statement in self.statements:
            yield from statement.iter_commands()


@dataclass(slots=True)
class Statement(Node):
    body: CommandLike | None = None
    terminator: str | None = None

    def iter_commands(self) -> Iterable[Command]:
        if self.body is not None:
            yield from self.body.iter_commands()


class CommandLike(Node):
    def iter_commands(self) -> Iterable[Command]:
        return iter(())


@dataclass(slots=True)
class ListExpr(CommandLike):
    op: str
    parts: list[CommandLike]

    def iter_commands(self) -> Iterable[Command]:
        for part in self.parts:
            yield from part.iter_commands()


@dataclass(slots=True)
class Pipeline(CommandLike):
    commands: list[CommandLike]
    negated: bool = False

    def iter_commands(self) -> Iterable[Command]:
        for command in self.commands:
            yield from command.iter_commands()


@dataclass(slots=True)
class Command(CommandLike):
    name: Word | None = None
    args: list[Word] = field(default_factory=list)
    redirects: list[Redirection] = field(default_factory=list)
    assignments: list[Assignment] = field(default_factory=list)
    raw_parts: list[str] = field(default_factory=list)

    def iter_commands(self) -> Iterable[Command]:
        yield self


@dataclass(slots=True)
class CompoundCommand(CommandLike):
    kind: str = "compound"
    text: str = ""

    def iter_commands(self) -> Iterable[Command]:
        return iter(())


@dataclass(slots=True)
class Assignment(Node):
    name: str
    value: str


@dataclass(slots=True)
class Redirection(Node):
    fd: int | None
    op: str
    target: Word


@dataclass(slots=True)
class Word(Node):
    text: str
    parts: list[WordPart] = field(default_factory=list)


@dataclass(slots=True)
class WordPart(Node):
    kind: str
    text: str
    parsed: Script | None = None


@dataclass(slots=True)
class HereDoc(Node):
    delimiter: str
    body: str
    strip_tabs: bool
    quoted_delimiter: bool
    parsed_parts: list[WordPart] = field(default_factory=list)


@dataclass(slots=True)
class ParseResult:
    script: Script
    elapsed_ms: float
