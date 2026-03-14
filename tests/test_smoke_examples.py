from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from bash_lark import BashParser

REPO_DIR = Path(__file__).resolve().parent / "fixtures" / "tree-sitter-bash"
EXAMPLES_DIR = REPO_DIR / "examples"


def ensure_examples() -> None:
    if EXAMPLES_DIR.exists():
        return
    REPO_DIR.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "https://github.com/tree-sitter/tree-sitter-bash.git",
            str(REPO_DIR),
        ],
        check=True,
    )


def collect_example_files() -> list[Path]:
    ensure_examples()
    files = [p for p in EXAMPLES_DIR.rglob("*") if p.is_file()]
    return sorted(files)


@pytest.mark.parametrize("path", collect_example_files())
def test_parses_tree_sitter_examples(path: Path) -> None:
    parser = BashParser()
    source = path.read_text(encoding="utf-8", errors="ignore")
    result = parser.parse(source)
    assert result.script is not None


@pytest.mark.parametrize(
    "source",
    [
        "echo $(echo nested $(date))",
        "cat <<EOF\nhello $(whoami)\nEOF\n",
        "diff <(ls -1) <(printf 'a\\nb\\n')",
        "for x in a b; do echo $x; done",
        "if true; then echo ok; else echo fail; fi",
        "cmd 2>/tmp/x >>out",
    ],
)
def test_representative_constructs(source: str) -> None:
    parser = BashParser()
    result = parser.parse(source)
    assert result.script is not None
