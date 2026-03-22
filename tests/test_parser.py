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
