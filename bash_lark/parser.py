from __future__ import annotations

import re
import time

from lark import Lark, Token, Transformer

from .ast import (
    Assignment,
    Command,
    HereDoc,
    ParseResult,
    Redirection,
    Script,
    Statement,
    Word,
    WordPart,
)
from .grammar import GRAMMAR


class AstBuilder(Transformer):
    def start(self, items):
        return items[0]

    def script(self, items):
        return Script(statements=[item for item in items if isinstance(item, Statement)])

    def statement(self, items):
        body = None
        term = None
        for item in items:
            if isinstance(item, Command):
                body = item
            elif isinstance(item, Token) and item.type == "SEP":
                term = str(item)
        return Statement(body=body, terminator=term)

    def command(self, items):
        cmd = Command()
        for part in items:
            if isinstance(part, Assignment):
                cmd.assignments.append(part)
            elif isinstance(part, Redirection):
                cmd.redirects.append(part)
            elif isinstance(part, Word):
                if cmd.name is None:
                    cmd.name = part
                else:
                    cmd.args.append(part)
                cmd.raw_parts.append(part.text)
        return cmd

    def assignment_word(self, items):
        name = str(items[0])
        value = items[1].text if len(items) > 1 and isinstance(items[1], Word) else ""
        return Assignment(name=name, value=value)

    def redirection(self, items):
        fd = None
        idx = 0
        if items and isinstance(items[0], Token) and items[0].type == "IO_NUMBER":
            fd = int(str(items[0]))
            idx = 1
        op = str(items[idx])
        target = items[idx + 1]
        if isinstance(target, Token):
            target = Word(text=str(target))
        return Redirection(fd=fd, op=op, target=target)

    def word(self, items):
        return items[0] if items and isinstance(items[0], Word) else Word(text=str(items[0]))

    def redir_target(self, items):
        return items[0]

    def WORD(self, token):
        return Word(text=str(token))

    def PROCESS_SUBST(self, token):
        return Word(text=str(token))


_SUB_REGEX = re.compile(r"(`[^`\n]*`|\$\([^\n)]*\)|[<>]\([^\n)]*\))")
_HEREDOC_REGEX = re.compile(r"<<-?\s*(?:'([^']+)'|\"([^\"]+)\"|([^\s;|&(){}<>]+))")


class BashParser:
    def __init__(self) -> None:
        self._parser = Lark(GRAMMAR, parser="lalr", maybe_placeholders=False)
        self._sub_parser = Lark(GRAMMAR, parser="lalr", start="script", maybe_placeholders=False)
        self._builder = AstBuilder()

    def parse(self, source: str) -> ParseResult:
        started = time.perf_counter()
        tree = self._parser.parse(source)
        script = self._builder.transform(tree)
        script.here_docs = self._extract_heredocs(source)
        self._attach_word_parts(script)
        return ParseResult(script=script, elapsed_ms=(time.perf_counter() - started) * 1000.0)

    def _attach_word_parts(self, script: Script) -> None:
        for command in script.iter_commands():
            words: list[Word] = []
            if command.name:
                words.append(command.name)
            words.extend(command.args)
            words.extend(redir.target for redir in command.redirects)
            for word in words:
                word.parts = self._parse_word_parts(word.text)
        for here_doc in script.here_docs:
            if not here_doc.quoted_delimiter:
                here_doc.parsed_parts = self._parse_word_parts(here_doc.body)

    def _parse_word_parts(self, text: str) -> list[WordPart]:
        parts: list[WordPart] = []
        last = 0
        for m in _SUB_REGEX.finditer(text):
            if m.start() > last:
                parts.append(WordPart(kind="literal", text=text[last : m.start()]))
            fragment = m.group(0)
            kind = "process_substitution" if fragment[:2] in {"<(", ">("} else "command_substitution"
            parts.append(WordPart(kind=kind, text=fragment, parsed=self._parse_embedded(fragment)))
            last = m.end()
        if last < len(text):
            parts.append(WordPart(kind="literal", text=text[last:]))
        if not parts:
            parts.append(WordPart(kind="literal", text=text))
        return parts

    def _parse_embedded(self, fragment: str) -> Script | None:
        if fragment.startswith("`") and fragment.endswith("`"):
            content = fragment[1:-1]
        elif fragment.startswith("$(") and fragment.endswith(")"):
            content = fragment[2:-1]
        elif (fragment.startswith("<(") or fragment.startswith(">(")) and fragment.endswith(")"):
            content = fragment[2:-1]
        else:
            return None
        try:
            tree = self._sub_parser.parse(content)
            return self._builder.transform(tree)
        except Exception:
            return None

    def _extract_heredocs(self, source: str) -> list[HereDoc]:
        lines = source.splitlines()
        queue: list[tuple[str, bool, bool]] = []
        docs: list[HereDoc] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            for match in _HEREDOC_REGEX.finditer(line):
                delimiter = match.group(1) or match.group(2) or match.group(3) or ""
                queue.append((delimiter, line[match.start():].startswith("<<-"), bool(match.group(1) or match.group(2))))
            i += 1
            while queue and i < len(lines):
                delimiter, strip_tabs, quoted = queue.pop(0)
                body_lines: list[str] = []
                while i < len(lines):
                    current = lines[i]
                    comparable = current.lstrip("\t") if strip_tabs else current
                    if comparable == delimiter:
                        break
                    body_lines.append(current)
                    i += 1
                docs.append(HereDoc(delimiter=delimiter, body="\n".join(body_lines), strip_tabs=strip_tabs, quoted_delimiter=quoted))
                i += 1
        return docs
