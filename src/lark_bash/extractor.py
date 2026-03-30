from __future__ import annotations

import re

from lark import Token, Tree, Visitor

from .model import CommandRecord, HeredocRecord, SourceSpan, SubstitutionRecord
from .subparsers import SubstitutionParser


class BashCommandExtractor(Visitor):
    def __init__(self, source: str = "", heredocs: list[HeredocRecord] | None = None) -> None:
        self.records: list[CommandRecord] = []
        self._sub_parser = SubstitutionParser()
        self._heredocs = heredocs or []

    def simple_command(self, tree: Tree) -> None:
        assignments: list[str] = []
        redirects: list[str] = []
        args: list[str] = []
        substitutions: list[SubstitutionRecord] = []
        name: str | None = None

        for child in tree.children:
            if not isinstance(child, Tree):
                continue
            if child.data == "cmd_prefix":
                self._collect_prefix(child, assignments, redirects, substitutions)
            elif child.data == "cmd_word":
                name, subs = self._word_value_and_subs(child.children[0])
                substitutions.extend(subs)
            elif child.data == "cmd_suffix":
                for suffix_item in child.children:
                    if isinstance(suffix_item, Tree) and suffix_item.data == "arg":
                        value, subs = self._word_value_and_subs(suffix_item.children[0])
                        args.append(value)
                        substitutions.extend(subs)
                    elif isinstance(suffix_item, Tree) and suffix_item.data.startswith("redirect"):
                        redirects.append(self._flatten(suffix_item))
                        substitutions.extend(self._subs_from_node(suffix_item))

        span = None
        if hasattr(tree, "meta"):
            span = SourceSpan(tree.meta.line, tree.meta.column, tree.meta.end_line, tree.meta.end_column)

        self.records.append(
            CommandRecord(
                name=name,
                args=args,
                redirects=redirects,
                assignments=assignments,
                substitutions=substitutions,
                heredocs=self._heredocs_for_span(span),
                source_span=span,
                raw_node=tree,
            )
        )

    def _collect_prefix(self, node: Tree, assignments: list[str], redirects: list[str], substitutions: list[SubstitutionRecord]) -> None:
        for item in node.children:
            if isinstance(item, Tree) and item.data == "assignment":
                assignments.append(self._flatten(item))
            elif isinstance(item, Tree) and item.data.startswith("redirect"):
                redirects.append(self._flatten(item))
                substitutions.extend(self._subs_from_node(item))

    def _word_value_and_subs(self, word_node: Tree) -> tuple[str, list[SubstitutionRecord]]:
        raw = self._flatten(word_node)
        subs = self._subs_from_node(word_node)
        if any(isinstance(c, Tree) and c.data == "double_quoted" for c in word_node.children):
            subs.extend(self._subs_from_text(raw))
        return raw, subs

    def _subs_from_text(self, raw: str) -> list[SubstitutionRecord]:
        out: list[SubstitutionRecord] = []
        for match in re.findall(r"\$\((?:[^()]|\([^()]*\))*\)", raw):
            out.append(self._build_substitution_record("command_substitution", match))
        return out

    def _build_substitution_record(self, kind: str, raw: str) -> SubstitutionRecord:
        inner = raw
        if raw.startswith("$(") and raw.endswith(")"):
            inner = raw[2:-1]
        elif raw.startswith("`") and raw.endswith("`"):
            inner = raw[1:-1]
        elif raw.startswith("${") and raw.endswith("}"):
            inner = raw[2:-1]
        elif raw.startswith("$((") and raw.endswith("))"):
            inner = raw[3:-2]

        subtree = None
        try:
            subtree = self._sub_parser.parse(inner + "\n")
            extract_commands(subtree)
        except Exception:
            subtree = None
        return SubstitutionRecord(kind=kind, raw=raw, subtree=subtree)

    def _subs_from_node(self, node: Tree) -> list[SubstitutionRecord]:
        out: list[SubstitutionRecord] = []
        for item in node.iter_subtrees_topdown():
            if item.data in {"command_substitution", "backtick_substitution", "parameter_expansion", "arithmetic_expansion"}:
                out.append(self._build_substitution_record(item.data, self._flatten(item)))
        return out

    def _heredocs_for_span(self, span: SourceSpan | None) -> list[HeredocRecord]:
        if span is None:
            return []
        return [h for h in self._heredocs if span.start_line <= h.start_line <= span.end_line + 1]

    def _flatten(self, node: Tree) -> str:
        return "".join(item.value for item in node.scan_values(lambda x: isinstance(x, Token)))


def extract_commands(tree: Tree, source: str = "", heredocs: list[HeredocRecord] | None = None) -> list[CommandRecord]:
    extractor = BashCommandExtractor(source=source, heredocs=heredocs)
    extractor.visit(tree)
    return extractor.records
