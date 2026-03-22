from __future__ import annotations

from pathlib import Path

import pytest

from extractor import extract_commands
from parser import BashParser

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize(
    ("example_name", "expected_prefix"),
    [
        ("minimal.sh", ["echo", "bar", "baz"]),
        ("release.sh", ["unset", "set", "rm"]),
        ("update-authors.sh", ["git", "perl"]),
    ],
)
def test_example_scripts_parse(example_name: str, expected_prefix: list[str]) -> None:
    parser = BashParser()
    result = parser.parse_file(EXAMPLES_DIR / example_name)

    commands = extract_commands(result)

    assert result.source_path == EXAMPLES_DIR / example_name
    assert [command.name for command in commands[: len(expected_prefix)]] == expected_prefix
    assert commands
