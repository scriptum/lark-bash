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
