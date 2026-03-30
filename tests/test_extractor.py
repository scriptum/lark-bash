from lark_bash import BashParser, extract_commands


def test_extract_command_structure_without_heuristics() -> None:
    parser = BashParser()
    parsed = parser.parse_with_metadata("VAR=1 cmd arg1 arg2 >out 2>&1\n")
    records = extract_commands(parsed.tree, source=parsed.source, heredocs=parsed.heredocs)

    assert len(records) == 1
    rec = records[0]
    assert rec.name == "cmd"
    assert rec.args[:2] == ["arg1", "arg2"]
    assert rec.assignments == ["VAR=1"]
    assert rec.redirects


def test_substitution_subtree_is_stored() -> None:
    parser = BashParser()
    parsed = parser.parse_with_metadata('echo "$(echo $(date))"\n')
    records = extract_commands(parsed.tree, source=parsed.source, heredocs=parsed.heredocs)
    assert records[0].substitutions
    assert records[0].substitutions[0].subtree is not None
