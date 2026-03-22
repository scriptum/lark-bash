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
