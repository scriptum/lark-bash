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
