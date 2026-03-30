from __future__ import annotations

from lark import Tree

from .parser import BashParser


class SubstitutionParser:
    """Sub-parser for nested shell snippets.

    Reuses the main Bash parser recursively to avoid regex-based nesting handling.
    """

    def __init__(self) -> None:
        self._parser = BashParser()

    def parse(self, text: str) -> Tree:
        return self._parser.parse(text)
