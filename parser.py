from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from time import perf_counter
from typing import Optional

from lark import Lark, Tree

GRAMMAR_PATH = Path(__file__).parent / "grammar" / "bash_minimal.lark"
HEREDOC_PATTERN = re.compile(r"<<-?\s*(?P<quote>['\"]?)(?P<delimiter>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)")


@dataclass(slots=True)
class HereDocSource:
    operator: str
    delimiter: str
    body: str
    start_line: int
    end_line: int
    delimiter_line: int
    quoted: bool


@dataclass(slots=True)
class ParseResult:
    tree: Tree
    elapsed_ms: float
    source_path: Optional[Path] = None
    source_text: str = ""
    parsed_text: str = ""
    heredocs: list[HereDocSource] = field(default_factory=list)


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

    def parse(self, text: str, source_path: Optional[str | Path] = None) -> ParseResult:
        prepared = self._prepare_source(text)
        started = perf_counter()
        tree = self._parser.parse(prepared["parsed_text"])
        elapsed_ms = (perf_counter() - started) * 1000
        return ParseResult(
            tree=tree,
            elapsed_ms=elapsed_ms,
            source_path=Path(source_path) if source_path else None,
            source_text=text,
            parsed_text=prepared["parsed_text"],
            heredocs=prepared["heredocs"],
        )

    def parse_file(self, path: str | Path) -> ParseResult:
        file_path = Path(path)
        return self.parse(file_path.read_text(encoding="utf-8"), source_path=file_path)

    def _prepare_source(self, text: str) -> dict[str, str | list[HereDocSource]]:
        lines = text.splitlines(keepends=True)
        output: list[str] = []
        heredocs: list[HereDocSource] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            output.append(line)
            match = HEREDOC_PATTERN.search(line)
            if match is None:
                index += 1
                continue

            operator = "<<-" if "<<-" in match.group(0) else "<<"
            delimiter = match.group("delimiter")
            quoted = bool(match.group("quote"))
            body_lines: list[str] = []
            body_start_line = index + 2
            index += 1
            while index < len(lines):
                current = lines[index]
                body_candidate = current.rstrip("\n")
                compare_value = body_candidate.lstrip("\t") if operator == "<<-" else body_candidate
                if compare_value == delimiter:
                    heredocs.append(
                        HereDocSource(
                            operator=operator,
                            delimiter=delimiter,
                            body="".join(body_lines),
                            start_line=body_start_line,
                            end_line=index,
                            delimiter_line=index + 1,
                            quoted=quoted,
                        )
                    )
                    output.append("\n" if current.endswith("\n") else "")
                    break
                body_lines.append(current)
                output.append("\n" if current.endswith("\n") else "")
                index += 1
            index += 1
        return {"parsed_text": "".join(output), "heredocs": heredocs}


def main() -> None:
    import argparse

    cli = argparse.ArgumentParser(description="Parse a shell script with the minimal Lark grammar.")
    cli.add_argument("path", help="Path to a shell script")
    args = cli.parse_args()

    result = BashParser().parse_file(args.path)
    print(f"Parsed {args.path} in {result.elapsed_ms:.3f} ms")
    print(result.tree.pretty())


if __name__ == "__main__":
    main()
