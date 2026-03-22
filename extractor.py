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
    heredoc_id: int | None = None


@dataclass(slots=True)
class CommandRecord:
    command_id: int
    parent_command_id: int | None
    type: Literal["external", "builtin", "function_call", "assignment_only", "redirect_only"]
    name: str | None
    args: list[str]
    args_structured: list[list[WordPart]]
    args_expanded: list[list[SubParseRecord]]
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
            "command_id": self.command_id,
            "parent_command_id": self.parent_command_id,
            "type": self.type,
            "name": self.name,
            "command_name": self.name,
            "args": self.args,
            "args_structured": [[part.to_dict() for part in arg] for arg in self.args_structured],
            "args_expanded": [[record.to_dict() for record in arg] for arg in self.args_expanded],
            "redirects": [
                {
                    "operator": redirect.operator,
                    "fd": redirect.fd,
                    "target": redirect.target,
                    "kind": redirect.kind,
                    "heredoc_id": redirect.heredoc_id,
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
    subparses: list[SubParseRecord]


class CommandExtractor(Visitor):
    def __init__(self, result: ParseResult, parent_command_id: int | None = None) -> None:
        self.result = result
        self.parent_command_id = parent_command_id
        self.commands: list[CommandRecord] = []
        self._wrappers: list[str] = []
        self._subparsers = SubParserManager()
        self._next_command_id = 1
        self._word_parts_fallback = self._subparsers

    def simple_command(self, tree: Tree) -> None:
        command_id = self._next_command_id
        self._next_command_id += 1

        words: list[WordValue] = []
        assignments: list[str] = []
        redirects: list[RedirectRecord] = []
        subparses: list[SubParseRecord] = []
        args_expanded: list[list[SubParseRecord]] = []

        previous_word_node: Tree | None = None
        for part in [child for child in tree.children if isinstance(child, Tree)]:
            payload = self._unwrap_command_part(part)
            if payload is None:
                continue

            kind, node = payload
            if kind == "assignment":
                previous_word_node = None
                value = self._extract_assignment_value(node, command_id)
                assignments.append(value.raw)
                subparses.extend(value.subparses)
            elif kind == "word":
                value = self._extract_word_value(node, command_id)
                if words and self._is_adjacent(previous_word_node, node):
                    words[-1].raw += value.raw
                    words[-1].parts.extend(value.parts)
                    words[-1].subparses.extend(value.subparses)
                else:
                    words.append(value)
                subparses.extend(value.subparses)
                previous_word_node = node
            elif kind == "redirect":
                previous_word_node = None
                redirect_record, redirect_subparses = self._flatten_redirect(node, command_id)
                redirects.append(redirect_record)
                subparses.extend(redirect_subparses)

        if not words and not assignments and not redirects:
            return

        command_name = words[0].raw if words else None
        args = [word.raw for word in words[1:]] if len(words) > 1 else []
        args_structured = [word.parts for word in words[1:]] if len(words) > 1 else []
        args_expanded = [word.subparses for word in words[1:]] if len(words) > 1 else []
        meta = tree.meta

        self.commands.append(
            CommandRecord(
                command_id=command_id,
                parent_command_id=self.parent_command_id,
                type=self._classify_command(command_name, assignments, redirects),
                name=command_name,
                args=args,
                args_structured=args_structured,
                args_expanded=args_expanded,
                redirects=redirects,
                assignments=assignments,
                wrappers=list(self._wrappers),
                pipeline_id=None,
                pipeline_index=None,
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
        if tree.data in {"compound_command", "keyword_construct", "brace_group", "subshell", "if_clause", "while_clause", "until_clause", "for_clause", "select_clause", "case_clause", "test_clause", "arithmetic_command", "pipeline", "and_or", "function_definition", "bash_function_definition"}:
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
            return "assignment", node.children[0] if node.children and isinstance(node.children[0], Tree) else node
        if node.data == "word":
            return "word", node
        if node.data == "redirect":
            return "redirect", node
        return None

    def _extract_assignment_value(self, tree: Tree, command_id: int) -> WordValue:
        return WordValue(
            raw=self._flatten_tree(tree),
            parts=self._word_parts_for_assignment(tree),
            subparses=self._subparses_for_tree(tree, command_id),
        )

    def _flatten_redirect(self, tree: Tree, command_id: int) -> tuple[RedirectRecord, list[SubParseRecord]]:
        inner = tree.children[0] if tree.children and isinstance(tree.children[0], Tree) else tree
        fd = None
        operator = ""
        target = None
        target_parts: list[WordPart] = []
        target_subparses: list[SubParseRecord] = []
        for child in inner.children:
            if isinstance(child, Token) and child.type == "IO_NUMBER":
                fd = child.value
            elif isinstance(child, Token) and child.type == "REDIR_OP":
                operator = child.value
            elif isinstance(child, Tree) and child.data == "word":
                value = self._extract_word_value(child, command_id)
                target = value.raw
                target_parts = value.parts
                target_subparses = value.subparses
        heredoc_id = self.result.redirect_heredoc_map.get(self._node_span_key(tree))
        record = RedirectRecord(
            operator=operator,
            fd=fd,
            target=target,
            kind=self._classify_redirect(operator, target, target_parts),
            heredoc_id=heredoc_id,
        )
        records = list(target_subparses)
        if heredoc_id is not None:
            heredoc = self.result.heredoc_map[heredoc_id]
            records.append(self._subparsers.build_heredoc_record(heredoc, parent_command_id=command_id))
        return record, records

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

    def _extract_word_value(self, tree: Tree, command_id: int) -> WordValue:
        return WordValue(
            raw=self._flatten_tree(tree),
            parts=self._word_parts_for_word(tree),
            subparses=self._subparses_for_tree(tree, command_id),
        )

    def _word_parts_for_assignment(self, tree: Tree) -> list[WordPart]:
        return self._word_parts_fallback.extract_word_parts(self._flatten_tree(tree))

    def _word_parts_for_word(self, tree: Tree) -> list[WordPart]:
        return self._word_parts_fallback.extract_word_parts(self._flatten_tree(tree))

    def _subparses_for_tree(self, tree: Tree, command_id: int) -> list[SubParseRecord]:
        return self._subparsers.extract_for_text(
            self._flatten_tree(tree),
            start_line=getattr(tree.meta, "line", None) or 1,
            start_column=getattr(tree.meta, "column", None) or 1,
            parent_command_id=command_id,
        )

    def _classify_command(
        self,
        command_name: str | None,
        assignments: list[str],
        redirects: list[RedirectRecord],
    ) -> Literal["external", "builtin", "function_call", "assignment_only", "redirect_only"]:
        if command_name is None and assignments:
            return "assignment_only"
        if command_name is None and redirects:
            return "redirect_only"
        return "external"

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


    def _is_adjacent(self, left: Tree | None, right: Tree) -> bool:
        if left is None:
            return False
        return (
            getattr(left.meta, "end_line", None) == getattr(right.meta, "line", None)
            and getattr(left.meta, "end_column", None) == getattr(right.meta, "column", None)
        )

    def _node_span_key(self, node: Tree) -> tuple[int | None, int | None, int | None, int | None]:
        return (
            getattr(node.meta, "line", None),
            getattr(node.meta, "column", None),
            getattr(node.meta, "end_line", None),
            getattr(node.meta, "end_column", None),
        )


def extract_commands(result: ParseResult, parent_command_id: int | None = None) -> list[CommandRecord]:
    extractor = CommandExtractor(result, parent_command_id=parent_command_id)
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
