from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from lark import Token, Tree
from lark.visitors import Visitor

from parser import BashParser, ParseResult
from subparsers import SubParseRecord, SubParserManager


@dataclass(slots=True)
class WordPart:
    type: str
    value: str

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type, "value": self.value}


@dataclass(slots=True)
class RedirectRecord:
    operator: str
    fd: str | None
    target: str | None
    kind: Literal["file", "fd_dup", "heredoc", "herestring", "process_substitution"]


@dataclass(slots=True)
class CommandRecord:
    name: str | None
    args: list[str]
    args_structured: list[list[WordPart]]
    redirects: list[RedirectRecord]
    assignments: list[str]
    wrappers: list[str]
    pipeline_id: int | None
    pipeline_index: int | None
    source_span: dict[str, int | None]
    raw_node: str
    subparses: list[SubParseRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "args": self.args,
            "args_structured": [[part.to_dict() for part in arg] for arg in self.args_structured],
            "redirects": [
                {
                    "operator": redirect.operator,
                    "fd": redirect.fd,
                    "target": redirect.target,
                    "kind": redirect.kind,
                }
                for redirect in self.redirects
            ],
            "assignments": self.assignments,
            "wrappers": self.wrappers,
            "pipeline_id": self.pipeline_id,
            "pipeline_index": self.pipeline_index,
            "source_span": self.source_span,
            "raw_node": self.raw_node,
            "subparses": [record.to_dict() for record in self.subparses],
        }


@dataclass(slots=True)
class WordValue:
    raw: str
    parts: list[WordPart]


class CommandExtractor(Visitor):
    def __init__(self, result: ParseResult) -> None:
        self.result = result
        self.commands: list[CommandRecord] = []
        self._wrappers: list[str] = []
        self._subparsers = SubParserManager()
        self._heredocs = sorted(result.heredocs, key=lambda heredoc: (heredoc.redirect_line, heredoc.redirect_column))

    def simple_command(self, tree: Tree) -> None:
        words: list[WordValue] = []
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
                assignments.append(value)
                subparses.extend(self._subparses_for_node(value, node))
            elif kind == "word":
                value = self._extract_word_value(node)
                if (
                    value.raw.isdigit()
                    and index + 1 < len(parts)
                    and self._unwrap_command_part(parts[index + 1]) is not None
                    and self._unwrap_command_part(parts[index + 1])[0] == "redirect"
                    and self._is_adjacent(node, self._unwrap_command_part(parts[index + 1])[1])
                ):
                    redirect_node = self._unwrap_command_part(parts[index + 1])[1]
                    redirects.append(self._flatten_redirect(redirect_node, fd_override=value.raw))
                    subparses.extend(self._subparses_for_redirect(redirect_node))
                    index += 2
                    continue
                if words and self._is_adjacent(parts[index - 1], node):
                    words[-1].raw += value.raw
                    words[-1].parts.extend(value.parts)
                    subparses.extend(self._subparses_for_node(value.raw, node))
                    index += 1
                    continue
                words.append(value)
                subparses.extend(self._subparses_for_node(value.raw, node))
            elif kind == "redirect":
                redirects.append(self._flatten_redirect(node))
                subparses.extend(self._subparses_for_redirect(node))
            index += 1

        if not words and not assignments and not redirects:
            return

        command_name = words[0].raw if words else None
        args = [word.raw for word in words[1:]] if len(words) > 1 else []
        args_structured = [word.parts for word in words[1:]] if len(words) > 1 else []
        meta = tree.meta
        pipeline_id = None
        pipeline_index = None

        self.commands.append(
            CommandRecord(
                name=command_name,
                args=args,
                args_structured=args_structured,
                redirects=redirects,
                assignments=assignments,
                wrappers=list(self._wrappers),
                pipeline_id=pipeline_id,
                pipeline_index=pipeline_index,
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
        if tree.data in {"brace_group", "subshell", "if_clause", "while_clause", "until_clause", "for_clause", "case_clause", "pipeline", "and_or"}:
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
        target_parts: list[WordPart] = []
        for child in tree.children:
            if isinstance(child, Token) and child.type == "IO_NUMBER":
                fd = child.value
            elif isinstance(child, Token) and child.type == "REDIR_OP":
                operator = child.value
            elif isinstance(child, Tree) and child.data == "word":
                value = self._extract_word_value(child)
                target = value.raw
                target_parts = value.parts
        return RedirectRecord(
            operator=operator or "",
            fd=fd,
            target=target,
            kind=self._classify_redirect(operator or "", target, target_parts),
        )

    def _classify_redirect(self, operator: str, target: str | None, target_parts: list[WordPart]) -> Literal["file", "fd_dup", "heredoc", "herestring", "process_substitution"]:
        if operator in {"<<", "<<-"}:
            return "heredoc"
        if operator == "<<<":
            return "herestring"
        if any(part.type == "process_substitution" for part in target_parts):
            return "process_substitution"
        if operator in {"<&", ">&"} and target is not None and (target.isdigit() or target == "-"):
            return "fd_dup"
        return "file"

    def _extract_word_value(self, tree: Tree) -> WordValue:
        raw = self._flatten_tree(tree)
        parts = self._subparsers.extract_word_parts(raw)
        return WordValue(raw=raw, parts=parts)

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
                target_text = self._extract_word_value(child).raw
        if target_text is not None and target_node is not None:
            records.extend(self._subparses_for_node(target_text, target_node))
        heredoc = self._match_heredoc(node)
        if operator in {"<<", "<<-"} and heredoc is not None:
            record = self._subparsers.build_heredoc_record(heredoc)
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

    def _match_heredoc(self, node: Tree):
        line = getattr(node.meta, "line", None)
        column = getattr(node.meta, "column", None)
        for index, heredoc in enumerate(self._heredocs):
            if heredoc.redirect_line == line and heredoc.redirect_column == column:
                return self._heredocs.pop(index)
        for index, heredoc in enumerate(self._heredocs):
            if heredoc.redirect_line == line:
                return self._heredocs.pop(index)
        return None


def extract_commands(result: ParseResult) -> list[CommandRecord]:
    extractor = CommandExtractor(result)
    extractor.visit_topdown(result.tree)
    _assign_pipeline_metadata(result.tree, extractor.commands)
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


def _assign_pipeline_metadata(tree: Tree, commands: list[CommandRecord]) -> None:
    command_map = {
        (command.source_span["start_line"], command.source_span["start_column"], command.source_span["end_line"], command.source_span["end_column"]): command
        for command in commands
    }
    pipeline_id = 0
    for pipeline in tree.find_data("pipeline"):
        members: list[CommandRecord] = []
        for node in pipeline.find_data("simple_command"):
            key = (getattr(node.meta, "line", None), getattr(node.meta, "column", None), getattr(node.meta, "end_line", None), getattr(node.meta, "end_column", None))
            command = command_map.get(key)
            if command is not None:
                members.append(command)
        if len(members) <= 1:
            continue
        for index, command in enumerate(members):
            command.pipeline_id = pipeline_id
            command.pipeline_index = index
        pipeline_id += 1
