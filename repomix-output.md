This file is a merged representation of a subset of the codebase, containing specifically included files, combined into a single document by Repomix.

# File Summary

## Purpose
This file contains a packed representation of a subset of the repository's contents that is considered the most important context.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Only files matching these patterns are included: **/*.lark, **/*.py
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
grammar/
  bash_minimal.lark
  heredoc_scan.lark
  subparsers.lark
  word_parts.lark
scripts/
  debug_extract.py
tests/
  conftest.py
  test_examples.py
  test_iteration_upgrade.py
  test_parser.py
  test_subparsers.py
benchmark.py
extractor.py
parser.py
subparsers.py
```

# Files

## File: grammar/heredoc_scan.lark
```
start: fragment*

?fragment: heredoc | text | sq | dq

heredoc: HEREDOC_OP heredoc_delimiter
heredoc_delimiter: DQ_DELIM | SQ_DELIM | BARE_DELIM

text: TEXT
sq: SQUOTE SQUOTE
  | SQUOTE SQ_TEXT SQUOTE
dq: DQUOTE DQUOTE
  | DQUOTE DQ_TEXT DQUOTE

HEREDOC_OP: "<<-" | "<<"
DQ_DELIM: /"[^"]+"/
SQ_DELIM: /'[^']+'/
BARE_DELIM: /[A-Za-z_][A-Za-z0-9_]*/
TEXT: /(?:[^<'"\n]+|<(?!<))+/
SQUOTE: "'"
DQUOTE: "\""
SQ_TEXT: /[^']+/
DQ_TEXT: /(?:[^"\\]|\\.)+/
```

## File: grammar/subparsers.lark
```
start: fragment*

?fragment: command_substitution
         | process_substitution_in
         | process_substitution_out
         | arithmetic_expansion
         | backticks
         | parenthesized
         | text

command_substitution: DOLLAR_LPAR fragment* RPAR
process_substitution_in: LESS_LPAR fragment* RPAR
process_substitution_out: GREATER_LPAR fragment* RPAR
arithmetic_expansion: DOLLAR_DBL_LPAR arithmetic_fragment* DBL_RPAR
backticks: BACKTICK backtick_fragment* BACKTICK
parenthesized: LPAR fragment* RPAR

?backtick_fragment: command_substitution
                  | process_substitution_in
                  | process_substitution_out
                  | arithmetic_expansion
                  | escaped_backtick
                  | bt_text

?arithmetic_fragment: command_substitution
                    | process_substitution_in
                    | process_substitution_out
                    | arithmetic_text

text: TEXT
bt_text: BT_TEXT
arithmetic_text: ARITHMETIC_TEXT
escaped_backtick: ESCAPED_BACKTICK

DOLLAR_LPAR: "$("
LESS_LPAR: "<("
GREATER_LPAR: ">(" 
DOLLAR_DBL_LPAR: "$(("
DBL_RPAR: "))"
BACKTICK: "`"
LPAR: "("
RPAR: ")"
ESCAPED_BACKTICK: /\\./
TEXT: /(?:[^`$<>()\\]+|\\.|\$(?!\()|<(?!\()|>(?!\())+/
BT_TEXT: /(?:[^`\\]+|\\.)+/
ARITHMETIC_TEXT: /(?:[^$<>()]+|\$(?!\()|<(?!\()|>(?!\())+/
```

## File: grammar/word_parts.lark
```
start: part+

?part: param_expansion
     | arithmetic_expansion
     | command_substitution
     | process_substitution
     | quoted_literal
     | literal

param_expansion: PARAM_EXPANSION
arithmetic_expansion: ARITHMETIC_EXPANSION
command_substitution: COMMAND_SUBSTITUTION
process_substitution: PROCESS_SUBSTITUTION
quoted_literal: QUOTED_LITERAL
literal: LITERAL

PARAM_EXPANSION.20: /\$\{[^\n]*?\}|\$(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[-!$?@#*])/
ARITHMETIC_EXPANSION.21: /\$\(\([^\n]*?\)\)/
COMMAND_SUBSTITUTION.20: /\$\((?:[^()\n]|\([^()\n]*\))*\)|`[^\n]*?`/
PROCESS_SUBSTITUTION.20: /<\((?:[^()\n]|\([^()\n]*\))*\)|>\((?:[^()\n]|\([^()\n]*\))*\)/
QUOTED_LITERAL.15: /"(?:[^"\\]|\\.)*"|'[^']*'/
LITERAL: /(?:[^\s\\"'$`<>()]+|\\.)+/
```

## File: tests/conftest.py
```python
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

## File: tests/test_iteration_upgrade.py
```python
from __future__ import annotations

from time import perf_counter

from extractor import extract_commands
from parser import BashParser


def test_command_types_and_parent_links() -> None:
    parser = BashParser()
    parsed = parser.parse('FOO=bar\n> out\necho $(date)\n')
    commands = extract_commands(parsed)
    assert [command.type for command in commands] == ['assignment_only', 'redirect_only', 'external']
    assert commands[2].subparses[0].commands[0].parent_command_id == commands[2].command_id


def test_args_expanded_tracks_nested_subparses() -> None:
    parser = BashParser()
    parsed = parser.parse('echo foo$(bar)baz >(tee log)\n')
    command = extract_commands(parsed)[0]
    assert [record.kind for record in command.args_expanded[0]] == ['command_substitution']
    assert [record.kind for record in command.args_expanded[1]] == ['process_substitution_out']


def test_heredoc_redirect_mapping_uses_ids() -> None:
    parser = BashParser()
    parsed = parser.parse('cat <<EOF\n$(date)\nEOF\n')
    command = extract_commands(parsed)[0]
    redirect = command.redirects[0]
    assert redirect.heredoc_id is not None
    assert parsed.heredoc_map[redirect.heredoc_id].body == '$(date)\n'


def test_nested_pipeline_parentheses_parse() -> None:
    parser = BashParser()
    parsed = parser.parse('a | (b | c) | d\n')
    commands = extract_commands(parsed)
    assert [command.name for command in commands] == ['a', 'b', 'c', 'd']


def test_indented_heredoc_is_preserved() -> None:
    parser = BashParser()
    parsed = parser.parse('cat <<-EOF\n\tindented\nEOF\n')
    command = extract_commands(parsed)[0]
    heredoc = [record for record in command.subparses if record.kind == 'heredoc'][0]
    assert heredoc.raw_text == '\tindented\n'


def test_large_script_parse_budget() -> None:
    parser = BashParser()
    source = ''.join(f'echo line{i} $(date)\n' for i in range(50))
    started = perf_counter()
    parsed = parser.parse(source)
    elapsed_ms = (perf_counter() - started) * 1000
    commands = extract_commands(parsed)
    assert len(commands) == 50
    assert elapsed_ms < 10000
```

## File: tests/test_subparsers.py
```python
from __future__ import annotations

from extractor import extract_commands
from parser import BashParser


def test_command_substitution_subparser() -> None:
    parsed = BashParser().parse('echo $(date)\n')
    commands = extract_commands(parsed)
    assert [command.name for command in commands] == ['echo']
    assert len(commands[0].subparses) == 1
    subparse = commands[0].subparses[0]
    assert subparse.kind == 'command_substitution'
    assert [command.name for command in subparse.commands] == ['date']
    assert subparse.source_span['start_line'] == 1


def test_backticks_subparser() -> None:
    parsed = BashParser().parse('echo `date`\n')
    commands = extract_commands(parsed)
    assert [command.name for command in commands] == ['echo']
    assert len(commands[0].subparses) == 1
    assert commands[0].subparses[0].kind == 'backticks'
    assert [command.name for command in commands[0].subparses[0].commands] == ['date']


def test_process_substitution_subparser() -> None:
    parsed = BashParser().parse('diff <(ls dir1) <(ls dir2)\n')
    commands = extract_commands(parsed)
    assert [command.name for command in commands] == ['diff']
    process_nodes = [record for record in commands[0].subparses if record.kind == 'process_substitution_in']
    assert len(process_nodes) == 2
    assert [[command.name for command in record.commands] for record in process_nodes] == [['ls'], ['ls']]


def test_simple_heredoc_subparser() -> None:
    parsed = BashParser().parse('cat <<EOF\necho hi\nEOF\n')
    commands = extract_commands(parsed)
    assert [command.name for command in commands] == ['cat']
    heredocs = [record for record in commands[0].subparses if record.kind == 'heredoc']
    assert len(heredocs) == 1
    assert heredocs[0].delimiter == 'EOF'
    assert heredocs[0].expansion_enabled is True
    assert [command.name for command in heredocs[0].commands] == ['echo']
    assert heredocs[0].source_span['start_line'] == 2


def test_quoted_heredoc_stays_literal() -> None:
    parsed = BashParser().parse("cat <<'EOF'\necho hi\nEOF\n")
    commands = extract_commands(parsed)
    heredocs = [record for record in commands[0].subparses if record.kind == 'heredoc']
    assert len(heredocs) == 1
    assert heredocs[0].expansion_enabled is False
    assert heredocs[0].commands == []


def test_arithmetic_expansion_is_structural_subparse() -> None:
    parsed = BashParser().parse('echo $((1 + 2))\n')
    command = extract_commands(parsed)[0]
    arithmetic = [record for record in command.subparses if record.kind == 'arithmetic_expansion']
    assert len(arithmetic) == 1
    assert arithmetic[0].mode == 'arithmetic'
    assert arithmetic[0].commands == []
    assert arithmetic[0].depth == 1
```

## File: benchmark.py
```python
from __future__ import annotations

import argparse
from time import perf_counter

from extractor import extract_commands
from parser import BashParser


def main() -> None:
    cli = argparse.ArgumentParser(description="Benchmark the minimal Bash parser.")
    cli.add_argument("path", help="Path to a shell script")
    cli.add_argument("--with-extractor", action="store_true", help="Also run the command extractor")
    args = cli.parse_args()

    parser = BashParser()
    parsed = parser.parse_file(args.path)
    print(f"Parse time: {parsed.elapsed_ms:.3f} ms")
    print(parsed.tree.pretty())

    if args.with_extractor:
        started = perf_counter()
        commands = extract_commands(parsed)
        elapsed_ms = (perf_counter() - started) * 1000
        print(f"Extractor time: {elapsed_ms:.3f} ms")
        print(f"Extracted commands: {len(commands)}")


if __name__ == "__main__":
    main()
```

## File: scripts/debug_extract.py
```python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extractor import extract_commands
from parser import BashParser


def main() -> None:
    cli = argparse.ArgumentParser(description="Debug parse tree and extracted command records.")
    cli.add_argument("path", help="Path to a shell script")
    args = cli.parse_args()

    parsed = BashParser().parse_file(args.path)
    commands = extract_commands(parsed)

    print("=== Parse Tree ===")
    print(parsed.tree.pretty())
    print("=== Commands ===")
    print(json.dumps([command.to_dict() for command in commands], indent=2))
    print("=== Word Parts ===")
    word_parts = [
        {
            "command_id": command.command_id,
            "name": command.name,
            "args_structured": [[part.to_dict() for part in arg] for arg in command.args_structured],
            "args_expanded": [[record.to_dict() for record in arg] for arg in command.args_expanded],
        }
        for command in commands
    ]
    print(json.dumps(word_parts, indent=2))
    print("=== Subparses ===")
    print(
        json.dumps(
            [
                {
                    "command_id": command.command_id,
                    "name": command.name,
                    "subparses": [record.to_dict() for record in command.subparses],
                }
                for command in commands
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
```

## File: tests/test_examples.py
```python
from __future__ import annotations

from pathlib import Path

import pytest

from extractor import extract_commands
from parser import BashParser

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize(
    ("example_name", "expected_prefix"),
    [
        pytest.param("atom.sh", ["echo", "exit"], marks=pytest.mark.xfail(reason="example still uses unsupported multiline case/[ ... ] patterns", strict=False)),
        ("clean-old.sh", ["which", "which", "echo"]),
        pytest.param("doc-build.sh", ["set", "set", "cat"], marks=pytest.mark.xfail(reason="example still uses unsupported ! [ ... ] and multiline case forms", strict=False)),
        pytest.param("install.sh", ["curl", "rm", "echo"], marks=pytest.mark.xfail(reason="example still uses unsupported POSIX [ ... ] forms in many branches", strict=False)),
        ("minimal.sh", ["echo", "bar", "baz"]),
        ("relocate.sh", ["sed", "echo", "cat"]),
        ("release.sh", ["unset", "set", "rm"]),
        pytest.param("test.sh", ["cat", "usage"], marks=pytest.mark.xfail(reason="example still uses unsupported multiline case/test constructs", strict=False)),
        ("update-authors.sh", ["git", "perl"]),
    ],
)
def test_example_scripts_parse(example_name: str, expected_prefix: list[str]) -> None:
    parser = BashParser()
    result = parser.parse_file(EXAMPLES_DIR / example_name)

    commands = extract_commands(result)

    named_commands = [command.name for command in commands if command.name is not None]

    assert result.source_path == EXAMPLES_DIR / example_name
    assert named_commands[: len(expected_prefix)] == expected_prefix
    assert commands
```

## File: tests/test_parser.py
```python
from __future__ import annotations

import pytest

from extractor import extract_commands
from parser import BashParser


@pytest.fixture(scope="module")
def parser() -> BashParser:
    return BashParser()


@pytest.mark.parametrize(
    ("source", "expected_commands"),
    [
        ("echo hi\n", ["echo"]),
        ("VAR=value cmd arg\n", ["cmd"]),
        ("echo one; echo two\n", ["echo", "echo"]),
        ("echo one && echo two || echo three\n", ["echo", "echo", "echo"]),
        ("cat < in > out\n", ["cat"]),
        ("a | b | c\n", ["a", "b", "c"]),
        ("! a | b\n", ["a", "b"]),
        ("# comment only\n", []),
        ("echo hi   ", ["echo"]),
        ("echo hi;\n", ["echo"]),
        ("{ echo hi; }\n", ["echo"]),
        ("( echo hi )\n", ["echo"]),
        ("if cmd; then echo ok; fi\n", ["cmd", "echo"]),
        ("while cmd; do echo ok; done\n", ["cmd", "echo"]),
        ("until cmd; do echo ok; done\n", ["cmd", "echo"]),
        ("for i in a b; do echo \"$i\"; done\n", ["echo"]),
        ("case \"$x\" in a|b) echo 1 ;; esac\n", ["echo"]),
        ("foo() { echo hi; }\nfoo arg\n", ["echo", "foo"]),
    ],
)
def test_parser_smoke(parser: BashParser, source: str, expected_commands: list[str]) -> None:
    result = parser.parse(source)
    commands = extract_commands(result)
    assert [command.name for command in commands] == expected_commands


def test_redirects_and_assignments(parser: BashParser) -> None:
    result = parser.parse("VAR=value cmd >out 2>&1 arg\n")
    commands = extract_commands(result)
    assert len(commands) == 1
    command = commands[0]
    assert command.name == "cmd"
    assert command.args == ["arg"]
    assert command.assignments == ["VAR=value"]
    assert [(redirect.operator, redirect.fd, redirect.target) for redirect in command.redirects] == [
        (">", None, "out"),
        (">&", "2", "1"),
    ]


def test_tree_contains_posix_compound_nodes(parser: BashParser) -> None:
    tree = parser.parse("if cmd; then echo ok; else echo no; fi\n").tree
    assert any(tree.find_pred(lambda node: node.data == "if_clause"))

    case_tree = parser.parse("case \"$x\" in a|b) echo 1 ;; esac\n").tree
    assert any(case_tree.find_pred(lambda node: node.data == "case_clause"))


def test_bash_extensions_parse_and_extract(parser: BashParser) -> None:
    result = parser.parse("function greet { echo hi; }\ngreet\n")
    commands = extract_commands(result)
    assert [command.name for command in commands] == ["echo", "greet"]


def test_parameter_and_arithmetic_expansions_are_words(parser: BashParser) -> None:
    result = parser.parse("echo ${HOME:-/tmp} $((1 + 2))\n")
    commands = extract_commands(result)
    assert len(commands) == 1
    assert commands[0].name == "echo"
    assert commands[0].args == ["${HOME:-/tmp}", "$((1 + 2))"]


def test_array_assignment_word_is_extracted_as_assignment(parser: BashParser) -> None:
    result = parser.parse("arr+=(three)\n")
    commands = extract_commands(result)
    assert len(commands) == 1
    assert commands[0].name is None
    assert commands[0].assignments == ["arr+=(three)"]


def test_bash_compound_nodes_exist(parser: BashParser) -> None:
    tree = parser.parse("if [[ -n $x ]]; then ((count++)); fi\n").tree
    assert any(tree.find_pred(lambda node: node.data == "test_clause"))
    assert any(tree.find_pred(lambda node: node.data == "arithmetic_command"))

    select_tree = parser.parse("select item in a b; do echo \"$item\"; done\n").tree
    assert any(select_tree.find_pred(lambda node: node.data == "select_clause"))


def test_redirect_kind_process_substitution_and_pipeline_metadata(parser: BashParser) -> None:
    result = parser.parse("a | cmd 2> >(tee log) | c\n")
    commands = extract_commands(result)
    assert [command.name for command in commands] == ["a", "cmd", "c"]
    assert [(command.pipeline_id, command.pipeline_index) for command in commands] == [(0, 0), (0, 1), (0, 2)]
    redirect = commands[1].redirects[0]
    assert (redirect.operator, redirect.fd, redirect.target, redirect.kind) == (">", "2", ">(tee log)", "process_substitution")


def test_mixed_expansion_word_parts(parser: BashParser) -> None:
    result = parser.parse("echo foo$(bar)baz\n")
    commands = extract_commands(result)
    assert commands[0].args == ["foo$(bar)baz"]
    assert [(part.type, part.value) for part in commands[0].args_structured[0]] == [
        ("literal", "foo"),
        ("command_substitution", "$(bar)"),
        ("literal", "baz"),
    ]


def test_assignment_only_and_redirect_only_have_no_command_name(parser: BashParser) -> None:
    assignment_only = extract_commands(parser.parse("A=B=C\n"))
    assert len(assignment_only) == 1
    assert assignment_only[0].name is None
    assert assignment_only[0].assignments == ["A=B=C"]

    redirect_only = extract_commands(parser.parse("> out\n"))
    assert len(redirect_only) == 1
    assert redirect_only[0].name is None
    assert redirect_only[0].redirects[0].kind == "file"


def test_multiple_heredocs_are_attached_to_matching_redirects(parser: BashParser) -> None:
    result = parser.parse("cat <<EOF1 <<EOF2\na\nEOF1\nb\nEOF2\n")
    commands = extract_commands(result)
    heredocs = [record for record in commands[0].subparses if record.kind == "heredoc"]
    assert [redirect.kind for redirect in commands[0].redirects] == ["heredoc", "heredoc"]
    assert [record.delimiter for record in heredocs] == ["EOF1", "EOF2"]
    assert [record.raw_text for record in heredocs] == ["a\n", "b\n"]


def test_nested_substitutions_create_nested_subparses(parser: BashParser) -> None:
    result = parser.parse("echo $(echo $(date))\n")
    commands = extract_commands(result)
    outer = commands[0].subparses[0]
    assert outer.kind == "command_substitution"
    assert [command.name for command in outer.commands] == ["echo"]
    assert outer.commands[0].subparses[0].kind == "command_substitution"
    assert [command.name for command in outer.commands[0].subparses[0].commands] == ["date"]


def test_tree_classifies_compound_and_keyword_constructs(parser: BashParser) -> None:
    tree = parser.parse('if cmd; then { echo ok; } fi\n').tree
    assert any(tree.find_pred(lambda node: node.data == 'keyword_construct'))
    assert any(tree.find_pred(lambda node: node.data == 'compound_command'))


def test_keywords_and_functions_do_not_become_commands(parser: BashParser) -> None:
    result = parser.parse('foo() { echo hi; }\nif bar; then (( i++ )); fi\n')
    commands = extract_commands(result)
    assert [command.name for command in commands] == ['echo', 'bar']
    assert all(command.name not in {'if', 'then', 'fi', 'function'} for command in commands)


def test_posix_test_and_plain_parameter_words_parse(parser: BashParser) -> None:
    result = parser.parse('if [ -n "$HOME" ]; then echo $USER $$ $?; fi\n')
    commands = extract_commands(result)
    assert [command.name for command in commands] == ['echo']
    assert commands[0].args == ['$USER', '$$', '$?']
```

## File: parser.py
```python
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
    heredoc_id: int
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
    heredoc_map: dict[int, HereDocSource] = field(default_factory=dict)
    redirect_heredoc_map: dict[tuple[int | None, int | None, int | None, int | None], int] = field(default_factory=dict)


@dataclass(slots=True)
class PendingHereDoc:
    heredoc_id: int
    operator: str
    delimiter: str
    quoted: bool
    redirect_line: int
    redirect_column: int


class HereDocScanTransformer(Transformer):
    def __init__(self, next_heredoc_id: int) -> None:
        super().__init__()
        self._next_heredoc_id = next_heredoc_id

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
        pending = PendingHereDoc(
            heredoc_id=self._next_heredoc_id,
            operator=operator,
            delimiter=delimiter,
            quoted=quoted,
            redirect_line=0,
            redirect_column=redirect_column,
        )
        self._next_heredoc_id += 1
        return pending


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
        redirect_heredoc_map = self._build_redirect_heredoc_map(tree, prepared["heredocs"])
        return ParseResult(
            tree=tree,
            elapsed_ms=elapsed_ms,
            source_path=Path(source_path) if source_path else None,
            source_text=text,
            parsed_text=prepared["parsed_text"],
            heredocs=prepared["heredocs"],
            heredoc_map={heredoc.heredoc_id: heredoc for heredoc in prepared["heredocs"]},
            redirect_heredoc_map=redirect_heredoc_map,
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
        next_heredoc_id = 1
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
                                heredoc_id=current_pending.heredoc_id,
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
            scanned, next_heredoc_id = self._scan_heredocs(line, next_heredoc_id)
            for item in scanned:
                item.redirect_line = index + 1
            pending.extend(scanned)
            index += 1
        return {"parsed_text": "".join(output), "heredocs": heredocs}

    def _scan_heredocs(self, line: str, next_heredoc_id: int) -> tuple[list[PendingHereDoc], int]:
        try:
            tree = self._heredoc_scan_parser.parse(line.rstrip("\n"))
        except UnexpectedInput:
            return [], next_heredoc_id
        transformer = HereDocScanTransformer(next_heredoc_id)
        pending = transformer.transform(tree)
        return pending, transformer._next_heredoc_id

    def _build_redirect_heredoc_map(
        self,
        tree: Tree,
        heredocs: list[HereDocSource],
    ) -> dict[tuple[int | None, int | None, int | None, int | None], int]:
        heredoc_redirects: list[Tree] = []
        for redirect in tree.find_data("redirect"):
            operator = self._redirect_operator(redirect)
            if operator in {"<<", "<<-"}:
                heredoc_redirects.append(redirect)
        mapping: dict[tuple[int | None, int | None, int | None, int | None], int] = {}
        for redirect, heredoc in zip(heredoc_redirects, heredocs):
            key = (
                getattr(redirect.meta, "line", None),
                getattr(redirect.meta, "column", None),
                getattr(redirect.meta, "end_line", None),
                getattr(redirect.meta, "end_column", None),
            )
            mapping[key] = heredoc.heredoc_id
        return mapping

    def _redirect_operator(self, redirect: Tree) -> str | None:
        inner = redirect.children[0] if redirect.children and isinstance(redirect.children[0], Tree) else redirect
        for child in inner.children:
            if isinstance(child, Token) and child.type == "REDIR_OP":
                return child.value
        return None


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
```

## File: subparsers.py
```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from lark import Lark, Token, Transformer, Tree, UnexpectedInput, v_args

from parser import BashParser, HereDocSource, ParseResult

if TYPE_CHECKING:
    from extractor import CommandRecord

GRAMMAR_PATH = Path(__file__).parent / "grammar" / "subparsers.lark"
WORD_PARTS_GRAMMAR_PATH = Path(__file__).parent / "grammar" / "word_parts.lark"
MAX_SUBPARSE_DEPTH = 5
SubParseMode = Literal["command", "arithmetic", "test"]


@dataclass(slots=True)
class SubParseRecord:
    kind: str
    raw_text: str
    source_span: dict[str, int | None]
    tree_pretty: str
    commands: list[CommandRecord]
    delimiter: str | None = None
    expansion_enabled: bool | None = None
    mode: SubParseMode = "command"
    depth: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "raw_text": self.raw_text,
            "source_span": self.source_span,
            "tree_pretty": self.tree_pretty,
            "commands": [command.to_dict() for command in self.commands],
            "delimiter": self.delimiter,
            "expansion_enabled": self.expansion_enabled,
            "mode": self.mode,
            "depth": self.depth,
            "error": self.error,
        }


class NestedSubstitutionTransformer(Transformer):
    def __init__(
        self,
        manager: SubParserManager,
        base_line: int,
        base_column: int,
        depth: int,
        parent_command_id: int | None,
    ) -> None:
        super().__init__()
        self.manager = manager
        self.base_line = base_line
        self.base_column = base_column
        self.depth = depth
        self.parent_command_id = parent_command_id

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
        return self._build_record("command_substitution", tree, mode="command")

    @v_args(tree=True)
    def arithmetic_expansion(self, tree: Tree) -> SubParseRecord:
        return self._build_record("arithmetic_expansion", tree, mode="arithmetic")

    @v_args(tree=True)
    def process_substitution_in(self, tree: Tree) -> SubParseRecord:
        return self._build_record("process_substitution_in", tree, mode="command")

    @v_args(tree=True)
    def process_substitution_out(self, tree: Tree) -> SubParseRecord:
        return self._build_record("process_substitution_out", tree, mode="command")

    @v_args(tree=True)
    def backticks(self, tree: Tree) -> SubParseRecord:
        return self._build_record("backticks", tree, mode="command")

    def _build_record(self, kind: str, tree: Tree, mode: SubParseMode) -> SubParseRecord:
        raw_text = self._flatten(tree.children)
        payload = self._flatten(tree.children[1:-1])
        parsed, tree_pretty, commands, error = self.manager.parse_nested_shell(
            payload,
            depth=self.depth + 1,
            mode=mode,
            parent_command_id=self.parent_command_id,
        )
        return SubParseRecord(
            kind=kind,
            raw_text=raw_text,
            source_span={
                "start_line": self.base_line + getattr(tree.meta, "line", 1) - 1,
                "start_column": self._column_offset(getattr(tree.meta, "line", 1), getattr(tree.meta, "column", 1)),
                "end_line": self.base_line + getattr(tree.meta, "end_line", 1) - 1,
                "end_column": self._column_offset(getattr(tree.meta, "end_line", 1), getattr(tree.meta, "end_column", 1)),
            },
            tree_pretty=tree_pretty,
            commands=commands,
            mode=mode,
            depth=self.depth + 1,
            error=error,
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
        self._word_parts_parser = Lark.open(
            str(WORD_PARTS_GRAMMAR_PATH),
            parser="lalr",
            propagate_positions=True,
            maybe_placeholders=False,
            start="start",
        )
        self._shell_cache: dict[tuple[str, int, SubParseMode, int | None], tuple[ParseResult | None, str, list[CommandRecord], str | None]] = {}

    def extract_for_text(
        self,
        text: str,
        start_line: int,
        start_column: int,
        depth: int = 0,
        parent_command_id: int | None = None,
    ) -> list[SubParseRecord]:
        if depth >= MAX_SUBPARSE_DEPTH:
            return [self._failed_record("<depth-limit>", start_line, start_column, "maximum subparse depth exceeded")]
        try:
            tree = self._fragment_parser.parse(text)
        except UnexpectedInput as exc:
            return [self._failed_record(text, start_line, start_column, str(exc))]
        transformer = NestedSubstitutionTransformer(self, start_line, start_column, depth, parent_command_id)
        return transformer.transform(tree)


    def extract_word_parts(self, text: str) -> list[object]:
        from extractor import WordPart

        try:
            tree = self._word_parts_parser.parse(text)
        except UnexpectedInput:
            return [WordPart(type="literal", value=text)] if text else []
        parts: list[WordPart] = []
        type_map = {
            "literal": "literal",
            "quoted_literal": "literal",
            "param_expansion": "param_expansion",
            "arithmetic_expansion": "arithmetic_expansion",
            "command_substitution": "command_substitution",
            "process_substitution": "process_substitution",
        }
        for child in tree.children:
            if isinstance(child, Tree) and child.children and isinstance(child.children[0], Token):
                parts.append(WordPart(type=type_map[child.data], value=child.children[0].value))
        return parts

    def build_heredoc_record(
        self,
        heredoc: HereDocSource,
        depth: int = 0,
        parent_command_id: int | None = None,
    ) -> SubParseRecord:
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
                mode="command",
                depth=depth,
            )
        _, tree_pretty, commands, error = self.parse_nested_shell(
            heredoc.body,
            depth=depth + 1,
            mode="command",
            parent_command_id=parent_command_id,
        )
        return SubParseRecord(
            kind="heredoc",
            raw_text=heredoc.body,
            source_span={
                "start_line": heredoc.start_line,
                "start_column": 1,
                "end_line": heredoc.end_line,
                "end_column": None,
            },
            tree_pretty=tree_pretty,
            commands=commands,
            delimiter=heredoc.delimiter,
            expansion_enabled=True,
            mode="command",
            depth=depth,
            error=error,
        )

    def parse_nested_shell(
        self,
        payload: str,
        depth: int,
        mode: SubParseMode,
        parent_command_id: int | None,
    ) -> tuple[ParseResult | None, str, list[CommandRecord], str | None]:
        if depth >= MAX_SUBPARSE_DEPTH:
            return None, "<failed>", [], "maximum subparse depth exceeded"
        cache_key = (payload, depth, mode, parent_command_id)
        if cache_key in self._shell_cache:
            return self._shell_cache[cache_key]
        if mode != "command":
            result = (None, "", [], None)
        else:
            try:
                parsed = self._parser.parse(payload)
                commands = self._extract_commands(parsed, parent_command_id=parent_command_id)
                result = (parsed, parsed.tree.pretty(), commands, None)
            except UnexpectedInput as exc:
                result = (None, "<failed>", [], str(exc))
        self._shell_cache[cache_key] = result
        return result

    def _failed_record(self, raw_text: str, start_line: int, start_column: int, error: str, depth: int = 0) -> SubParseRecord:
        return SubParseRecord(
            kind="failed",
            raw_text=raw_text,
            source_span={
                "start_line": start_line,
                "start_column": start_column,
                "end_line": start_line,
                "end_column": start_column + len(raw_text),
            },
            tree_pretty="<failed>",
            commands=[],
            mode="command",
            depth=depth,
            error=error,
        )

    def _extract_commands(self, parsed: ParseResult, parent_command_id: int | None) -> list[CommandRecord]:
        from extractor import extract_commands

        return extract_commands(parsed, parent_command_id=parent_command_id)
```

## File: grammar/bash_minimal.lark
```
start: body
body: body_part*
body_part: SEP | and_or SEP?

clause_body: body_part+

and_or: pipeline ((AND_IF | OR_IF) pipeline)*
pipeline: BANG? command (PIPE command)*

command: function_definition
       | bash_function_definition
       | compound_command redirect*
       | keyword_construct
       | simple_command

simple_command: command_part+
command_part: assignment_word | redirect | word
assignment_word: ASSIGNMENT_WORD | ARRAY_ASSIGNMENT_WORD

compound_command: brace_group
                | subshell

keyword_construct: for_clause
                 | select_clause
                 | while_clause
                 | until_clause
                 | if_clause
                 | case_clause
                 | test_clause
                 | posix_test_clause
                 | arithmetic_command

brace_group: LBRACE body RBRACE
subshell: LPAR body RPAR

for_clause: FOR name for_words? SEP DO clause_body DONE
select_clause: SELECT name for_words? SEP DO clause_body DONE
for_words: IN wordlist?
wordlist: word+

while_clause: WHILE clause_body DO clause_body DONE
until_clause: UNTIL clause_body DO clause_body DONE

if_clause: IF clause_body THEN clause_body elif_clause* else_clause? FI
elif_clause: ELIF clause_body THEN clause_body
else_clause: ELSE clause_body

test_clause: DBL_LBRACK test_expression? DBL_RBRACK
posix_test_clause: SGL_LBRACK test_expression? SGL_RBRACK
test_expression: test_term+
test_term: word
         | AND_IF
         | OR_IF
         | BANG
         | LPAR test_expression RPAR

arithmetic_command: DBL_LPAR arithmetic_expression? DBL_RPAR
arithmetic_expression: arithmetic_term+
arithmetic_term: word
               | LPAR arithmetic_expression RPAR
               | BANG
               | AND_IF
               | OR_IF
               | PIPE
               | REDIR_OP

case_clause: CASE word IN case_item? case_item_cont* ESAC
case_item: pattern_list RPAR case_body DSEMI
case_item_cont: SEP+ pattern_list RPAR case_body DSEMI
case_body: body_part*
pattern_list: word (PIPE word)*

function_definition: FUNC_NAME function_body
bash_function_definition: FUNCTION name function_body
function_body: compound_command redirect*
name: NAME

redirect: fd_redirect | simple_redirect
fd_redirect: IO_NUMBER REDIR_OP word?
simple_redirect: REDIR_OP word?
word: EXPANSION_WORD
    | SUBSHELL_WORD
    | WORD
    | IO_NUMBER

AND_IF: "&&"
OR_IF: "||"
PIPE: "|"
BANG: "!"
DSEMI.10: ";;"
LBRACE: "{"
RBRACE: "}"
LPAR: "("
RPAR: ")"
DBL_LBRACK: "[["
DBL_RBRACK: "]]"
SGL_LBRACK: "["
SGL_RBRACK: "]"
DBL_LPAR: "(("
DBL_RPAR: "))"

FOR: "for"
SELECT: "select"
WHILE: "while"
UNTIL: "until"
DO: "do"
DONE: "done"
IF: "if"
THEN: "then"
ELIF: "elif"
ELSE: "else"
FI: "fi"
CASE: "case"
IN: "in"
ESAC: "esac"
FUNCTION: "function"

SEP: /(?:;|&)\n*|\n+/
IO_NUMBER.20: /[0-9]+/
FUNC_NAME.10: /[A-Za-z_][A-Za-z0-9_]*\(\)/
NAME: /[A-Za-z_][A-Za-z0-9_]*/
ASSIGNMENT_WORD: /[A-Za-z_][A-Za-z0-9_]*=(?:[^\s;|&<>(){}#\[\]\\$`"']|\\.|"(?:[^"\\]|\\.)*"|'[^']*'|\$\{[^\n]*?\}|\$\(\([^\n]*?\)\)|\$\((?:[^()\n]|\([^()\n]*\))*\)|`[^\n]*?`|<\((?:[^()\n]|\([^()\n]*\))*\)|>\((?:[^()\n]|\([^()\n]*\))*\)|\$(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[-!$?@#*]))*/
ARRAY_ASSIGNMENT_WORD.21: /(?:[A-Za-z_][A-Za-z0-9_]*\+=\([^\n]*\)|[A-Za-z_][A-Za-z0-9_]*=\([^\n]*\))/
REDIR_OP.20: "<<<" | "<<-" | "<<" | ">|" | ">>" | "<&" | ">&" | "<>" | "<" | ">"
EXPANSION_WORD.11: /\$\{[^\n]*?\}|\$\(\([^\n]*?\)\)|\$(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[-!$?@#*])/
SUBSHELL_WORD.30: /\$\((?:[^()\n]|\([^()\n]*\))*\)|`[^\n]*?`|<\((?:[^()\n]|\([^()\n]*\))*\)|>\((?:[^()\n]|\([^()\n]*\))*\)/
WORD: /(?:[^\s;|&<>(){}#\[\]\\$`"']|\\.|"(?:[^"\\]|\\.)*"|'[^']*')+/
COMMENT: /#[^\n]*/

%ignore /\\\n/
%ignore /[\t \f\r]+/
%ignore COMMENT
```

## File: extractor.py
```python
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
```
