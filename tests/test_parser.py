import pytest

from lark_bash import BashParser


@pytest.mark.parametrize(
    "snippet",
    [
        "if cmd; then echo ok; fi\n",
        "arr+=($(ls))\n",
        "cmd >out 2>&1\n",
        "cat <<EOF\n$(rm -rf /)\nEOF\n",
        "echo \"$(echo $(date))\"\n",
        "diff <(cmd1) <(cmd2)\n",
        "[[ \"$x\" == a* ]]\n",
        "(( i++ ))\n",
        "for i in a b; do echo \"$i\"; done\n",
    ],
)
def test_mandatory_edge_cases_parse(snippet: str) -> None:
    parser = BashParser()
    parser.parse(snippet)


def test_heredoc_metadata_extraction() -> None:
    parser = BashParser()
    parsed = parser.parse_with_metadata("cat <<'EOF'\n$(date)\nEOF\n")
    assert len(parsed.heredocs) == 1
    assert parsed.heredocs[0].quoted is True
