from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Optional

from lark import Lark, Token, Transformer, Tree, UnexpectedInput, v_args

GRAMMAR_PATH = Path(__file__).parent / "grammar" / "bash_minimal.lark"
HEREDOC_SCAN_GRAMMAR_PATH = Path(__file__).parent / "grammar" / "heredoc_scan.lark"


@dataclass(slots=True)
class HereDocSource:
    operator: str
    delimiter: str
    body: str
    start_line: int
    end_line: int
    delimiter_line: int
    quoted: bool
    redirect_line: int
    redirect_column: int


@dataclass(slots=True)
class ParseResult:
    tree: Tree
    elapsed_ms: float
    source_path: Optional[Path] = None
    source_text: str = ""
    parsed_text: str = ""
    heredocs: list[HereDocSource] = field(default_factory=list)


@dataclass(slots=True)
class PendingHereDoc:
    operator: str
    delimiter: str
    quoted: bool
    redirect_line: int
    redirect_column: int


class HereDocScanTransformer(Transformer):
    def start(self, children: list[object]) -> list[PendingHereDoc]:
        return [child for child in children if isinstance(child, PendingHereDoc)]

    @v_args(tree=True)
    def heredoc(self, tree: Tree) -> PendingHereDoc:
        operator = "<<"
        delimiter = ""
        quoted = False
        redirect_column = getattr(tree.meta, "column", 1)
        for child in tree.children:
            if isinstance(child, Token) and child.type == "HEREDOC_OP":
                operator = child.value
            elif isinstance(child, Tree) and child.data == "heredoc_delimiter":
                delimiter = "".join(token.value for token in child.scan_values(lambda value: isinstance(value, Token)))
                if len(delimiter) >= 2 and delimiter[0] == delimiter[-1] and delimiter[0] in {'"', "'"}:
                    quoted = True
                    delimiter = delimiter[1:-1]
        return PendingHereDoc(operator=operator, delimiter=delimiter, quoted=quoted, redirect_line=0, redirect_column=redirect_column)


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
        self._heredoc_scan_parser = Lark.open(
            str(HEREDOC_SCAN_GRAMMAR_PATH),
            parser="lalr",
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
        pending: list[PendingHereDoc] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            if pending:
                current_pending = pending[0]
                body_lines: list[str] = []
                body_start_line = index + 1
                while index < len(lines):
                    current = lines[index]
                    candidate = current.rstrip("\n")
                    compare_value = candidate.lstrip("\t") if current_pending.operator == "<<-" else candidate
                    if compare_value == current_pending.delimiter:
                        heredocs.append(
                            HereDocSource(
                                operator=current_pending.operator,
                                delimiter=current_pending.delimiter,
                                body="".join(body_lines),
                                start_line=body_start_line,
                                end_line=index,
                                delimiter_line=index + 1,
                                quoted=current_pending.quoted,
                                redirect_line=current_pending.redirect_line,
                                redirect_column=current_pending.redirect_column,
                            )
                        )
                        output.append("\n" if current.endswith("\n") else "")
                        pending.pop(0)
                        index += 1
                        break
                    body_lines.append(current)
                    output.append("\n" if current.endswith("\n") else "")
                    index += 1
                continue

            output.append(line)
            scanned = self._scan_heredocs(line)
            for item in scanned:
                item.redirect_line = index + 1
            pending.extend(scanned)
            index += 1
        return {"parsed_text": "".join(output), "heredocs": heredocs}

    def _scan_heredocs(self, line: str) -> list[PendingHereDoc]:
        try:
            tree = self._heredoc_scan_parser.parse(line.rstrip("\n"))
        except UnexpectedInput:
            return []
        return HereDocScanTransformer().transform(tree)


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
