from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lark import Lark, Tree

from .heredoc import HeredocParser
from .model import HeredocRecord

GRAMMAR_PATH = Path(__file__).resolve().parents[2] / "grammar" / "bash_main.lark"


@dataclass(slots=True)
class ParseResult:
    tree: Tree
    source: str
    heredocs: list[HeredocRecord]


class BashParser:
    def __init__(self) -> None:
        self._parser = Lark.open(
            str(GRAMMAR_PATH),
            parser="lalr",
            lexer="contextual",
            propagate_positions=True,
            maybe_placeholders=False,
            start="start",
        )
        self._heredoc_parser = HeredocParser()

    def parse(self, text: str) -> Tree:
        return self._parser.parse(text)

    def parse_file(self, path: str | Path) -> Tree:
        return self.parse(Path(path).read_text(encoding="utf-8"))

    def parse_with_metadata(self, text: str) -> ParseResult:
        tree = self.parse(text)
        heredocs = self._heredoc_parser.extract(text)
        return ParseResult(tree=tree, source=text, heredocs=heredocs)
