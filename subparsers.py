from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lark import Lark, Token, Transformer, Tree, v_args

from parser import BashParser, HereDocSource, ParseResult

if TYPE_CHECKING:
    from extractor import CommandRecord

GRAMMAR_PATH = Path(__file__).parent / "grammar" / "subparsers.lark"


@dataclass(slots=True)
class SubParseRecord:
    kind: str
    raw_text: str
    source_span: dict[str, int | None]
    tree_pretty: str
    commands: list[CommandRecord]
    delimiter: str | None = None
    expansion_enabled: bool | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "raw_text": self.raw_text,
            "source_span": self.source_span,
            "tree_pretty": self.tree_pretty,
            "commands": [command.to_dict() for command in self.commands],
            "delimiter": self.delimiter,
            "expansion_enabled": self.expansion_enabled,
        }


class NestedSubstitutionTransformer(Transformer):
    def __init__(self, manager: SubParserManager, base_line: int, base_column: int) -> None:
        super().__init__()
        self.manager = manager
        self.base_line = base_line
        self.base_column = base_column

    def start(self, children: list[Any]) -> list[SubParseRecord]:
        return [child for child in children if isinstance(child, SubParseRecord)]

    def text(self, children: list[Any]) -> str:
        return self._flatten(children)

    def bt_text(self, children: list[Any]) -> str:
        return self._flatten(children)

    def escaped_backtick(self, children: list[Any]) -> str:
        return self._flatten(children)

    def parenthesized(self, children: list[Any]) -> str:
        return self._flatten(children)

    @v_args(tree=True)
    def command_substitution(self, tree: Tree) -> SubParseRecord:
        return self._build_record("command_substitution", tree)

    @v_args(tree=True)
    def process_substitution_in(self, tree: Tree) -> SubParseRecord:
        return self._build_record("process_substitution_in", tree)

    @v_args(tree=True)
    def process_substitution_out(self, tree: Tree) -> SubParseRecord:
        return self._build_record("process_substitution_out", tree)

    @v_args(tree=True)
    def backticks(self, tree: Tree) -> SubParseRecord:
        return self._build_record("backticks", tree)

    def _build_record(self, kind: str, tree: Tree) -> SubParseRecord:
        raw_text = self._flatten(tree.children)
        payload = self._flatten(tree.children[1:-1])
        parsed = self.manager._parser.parse(payload)
        commands = self.manager._extract_commands(parsed)
        return SubParseRecord(
            kind=kind,
            raw_text=raw_text,
            source_span={
                "start_line": self.base_line + getattr(tree.meta, "line", 1) - 1,
                "start_column": self._column_offset(getattr(tree.meta, "line", 1), getattr(tree.meta, "column", 1)),
                "end_line": self.base_line + getattr(tree.meta, "end_line", 1) - 1,
                "end_column": self._column_offset(getattr(tree.meta, "end_line", 1), getattr(tree.meta, "end_column", 1)),
            },
            tree_pretty=parsed.tree.pretty(),
            commands=commands,
        )

    def _column_offset(self, line: int, column: int) -> int:
        return self.base_column + column - 1 if line == 1 else column

    def _flatten(self, items: list[Any]) -> str:
        flattened: list[str] = []
        for item in items:
            if isinstance(item, Token):
                flattened.append(item.value)
            elif isinstance(item, SubParseRecord):
                flattened.append(item.raw_text)
            elif isinstance(item, str):
                flattened.append(item)
            elif isinstance(item, list):
                flattened.append(self._flatten(item))
        return "".join(flattened)


class SubParserManager:
    def __init__(self) -> None:
        self._parser = BashParser()
        self._fragment_parser = Lark.open(
            str(GRAMMAR_PATH),
            parser="lalr",
            propagate_positions=True,
            maybe_placeholders=False,
            start="start",
        )

    def extract_for_text(self, text: str, start_line: int, start_column: int) -> list[SubParseRecord]:
        tree = self._fragment_parser.parse(text)
        transformer = NestedSubstitutionTransformer(self, start_line, start_column)
        return transformer.transform(tree)

    def build_heredoc_record(self, heredoc: HereDocSource) -> SubParseRecord | None:
        if heredoc.quoted:
            return SubParseRecord(
                kind="heredoc",
                raw_text=heredoc.body,
                source_span={
                    "start_line": heredoc.start_line,
                    "start_column": 1,
                    "end_line": heredoc.end_line,
                    "end_column": None,
                },
                tree_pretty="",
                commands=[],
                delimiter=heredoc.delimiter,
                expansion_enabled=False,
            )
        parsed = self._parser.parse(heredoc.body)
        commands = self._extract_commands(parsed)
        return SubParseRecord(
            kind="heredoc",
            raw_text=heredoc.body,
            source_span={
                "start_line": heredoc.start_line,
                "start_column": 1,
                "end_line": heredoc.end_line,
                "end_column": None,
            },
            tree_pretty=parsed.tree.pretty(),
            commands=commands,
            delimiter=heredoc.delimiter,
            expansion_enabled=True,
        )

    def _extract_commands(self, parsed: ParseResult) -> list[CommandRecord]:
        from extractor import extract_commands

        return extract_commands(parsed)
