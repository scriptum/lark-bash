from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from lark import Token, Tree
from lark.visitors import Visitor

from parser import BashParser, ParseResult
from subparsers import SubParseRecord, SubParserManager


@dataclass(slots=True)
class RedirectRecord:
    operator: str
    fd: str | None
    target: str | None


@dataclass(slots=True)
class CommandRecord:
    name: str | None
    args: list[str]
    redirects: list[RedirectRecord]
    assignments: list[str]
    wrappers: list[str]
    source_span: dict[str, int | None]
    raw_node: str
    subparses: list[SubParseRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "args": self.args,
            "redirects": [
                {"operator": redirect.operator, "fd": redirect.fd, "target": redirect.target}
                for redirect in self.redirects
            ],
            "assignments": self.assignments,
            "wrappers": self.wrappers,
            "source_span": self.source_span,
            "raw_node": self.raw_node,
            "subparses": [record.to_dict() for record in self.subparses],
        }


class CommandExtractor(Visitor):
    ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")

    def __init__(self, result: ParseResult) -> None:
        self.result = result
        self.commands: list[CommandRecord] = []
        self._wrappers: list[str] = []
        self._subparsers = SubParserManager()
        self._heredoc_index = 0

    def simple_command(self, tree: Tree) -> None:
        words: list[str] = []
        assignments: list[str] = []
        redirects: list[RedirectRecord] = []
        subparses: list[SubParseRecord] = []

        parts = [child for child in tree.children if isinstance(child, Tree)]
        index = 0
        while index < len(parts):
            part = parts[index]
            payload = self._unwrap_command_part(part)
            if payload is None:
                index += 1
                continue

            kind, node = payload
            if kind == "assignment":
                value = self._flatten_tree(node)
                if self.ASSIGNMENT_RE.match(value) and not words:
                    assignments.append(value)
                else:
                    words.append(value)
                subparses.extend(self._subparses_for_node(value, node))
            elif kind == "word":
                value = self._flatten_tree(node)
                if self.ASSIGNMENT_RE.match(value) and not words:
                    assignments.append(value)
                    subparses.extend(self._subparses_for_node(value, node))
                    index += 1
                    continue
                if (
                    value.isdigit()
                    and index + 1 < len(parts)
                    and self._unwrap_command_part(parts[index + 1]) is not None
                    and self._unwrap_command_part(parts[index + 1])[0] == "redirect"
                    and self._is_adjacent(node, self._unwrap_command_part(parts[index + 1])[1])
                ):
                    redirect_node = self._unwrap_command_part(parts[index + 1])[1]
                    redirects.append(self._flatten_redirect(redirect_node, fd_override=value))
                    subparses.extend(self._subparses_for_redirect(redirect_node))
                    index += 2
                    continue
                words.append(value)
                subparses.extend(self._subparses_for_node(value, node))
            elif kind == "redirect":
                redirects.append(self._flatten_redirect(node))
                subparses.extend(self._subparses_for_redirect(node))
            index += 1

        if not words and not assignments and not redirects:
            return

        command_name = words[0] if words else None
        args = words[1:] if len(words) > 1 else []
        meta = tree.meta
        self.commands.append(
            CommandRecord(
                name=command_name,
                args=args,
                redirects=redirects,
                assignments=assignments,
                wrappers=list(self._wrappers),
                source_span={
                    "start_line": getattr(meta, "line", None),
                    "start_column": getattr(meta, "column", None),
                    "end_line": getattr(meta, "end_line", None),
                    "end_column": getattr(meta, "end_column", None),
                },
                raw_node=" ".join(self._collect_tokens(tree)),
                subparses=subparses,
            )
        )

    def visit_topdown(self, tree: Tree) -> None:
        if tree.data in {"brace_group", "subshell", "if_clause", "while_clause", "until_clause", "for_clause", "case_clause"}:
            self._wrappers.append(tree.data)
            super().visit_topdown(tree)
            self._wrappers.pop()
            return
        super().visit_topdown(tree)

    def _unwrap_command_part(self, tree: Tree) -> tuple[str, Tree] | None:
        node = tree
        if node.data == "command_part" and node.children and isinstance(node.children[0], Tree):
            node = node.children[0]
        if node.data == "assignment_word":
            return "assignment", node
        if node.data == "word":
            return "word", node
        if node.data == "redirect":
            return "redirect", node
        return None

    def _flatten_redirect(self, tree: Tree, fd_override: str | None = None) -> RedirectRecord:
        fd = fd_override
        operator = None
        target = None
        for child in tree.children:
            if isinstance(child, Token) and child.type == "IO_NUMBER":
                fd = child.value
            elif isinstance(child, Token) and child.type == "REDIR_OP":
                operator = child.value
            elif isinstance(child, Tree) and child.data == "word":
                target = self._flatten_tree(child)
        return RedirectRecord(operator=operator or "", fd=fd, target=target)

    def _subparses_for_node(self, value: str, node: Tree) -> list[SubParseRecord]:
        return self._subparsers.extract_for_text(
            value,
            start_line=getattr(node.meta, "line", None) or 1,
            start_column=getattr(node.meta, "column", None) or 1,
        )

    def _subparses_for_redirect(self, node: Tree) -> list[SubParseRecord]:
        records: list[SubParseRecord] = []
        operator = None
        target_text = None
        target_node = None
        for child in node.children:
            if isinstance(child, Token) and child.type == "REDIR_OP":
                operator = child.value
            elif isinstance(child, Tree) and child.data == "word":
                target_node = child
                target_text = self._flatten_tree(child)
        if target_text is not None and target_node is not None:
            records.extend(self._subparses_for_node(target_text, target_node))
        if operator in {"<<", "<<-"} and self._heredoc_index < len(self.result.heredocs):
            record = self._subparsers.build_heredoc_record(self.result.heredocs[self._heredoc_index])
            self._heredoc_index += 1
            if record is not None:
                records.append(record)
        return records

    def _flatten_tree(self, tree: Tree) -> str:
        return "".join(self._collect_tokens(tree))

    def _collect_tokens(self, node: Tree) -> list[str]:
        items: list[str] = []
        for child in node.children:
            if isinstance(child, Token):
                items.append(child.value)
            elif isinstance(child, Tree):
                items.extend(self._collect_tokens(child))
        return items

    def _is_adjacent(self, left: Tree, right: Tree) -> bool:
        return (
            getattr(left.meta, "end_line", None) == getattr(right.meta, "line", None)
            and getattr(left.meta, "end_column", None) == getattr(right.meta, "column", None)
        )


def extract_commands(result: ParseResult) -> list[CommandRecord]:
    extractor = CommandExtractor(result)
    extractor.visit_topdown(result.tree)
    return extractor.commands


def main() -> None:
    import argparse
    import json

    cli = argparse.ArgumentParser(description="Extract command records from a shell script.")
    cli.add_argument("path", help="Path to a shell script")
    args = cli.parse_args()

    parsed = BashParser().parse_file(args.path)
    commands = extract_commands(parsed)
    print(json.dumps([command.to_dict() for command in commands], indent=2))


if __name__ == "__main__":
    main()
