# Bash parsing design for SAST

## Architecture baseline

1. Main parser: `grammar/bash_main.lark` with LALR + contextual lexer.
2. Extraction layer: `BashCommandExtractor` that reads only `Tree.data` nodes (`cmd_prefix/cmd_word/cmd_suffix`, redirects, etc.).
3. Nested sub-parsing: `SubstitutionParser` recursively reuses `BashParser` for substitution payloads.
4. Heredoc mini-parser: `HeredocParser` extracts delimiter/body metadata (`quoted` vs unquoted) from source text.

## POSIX-style command form

`simple_command` is normalized to POSIX-style layout:

- `simple_command: cmd_prefix? cmd_word cmd_suffix? | cmd_prefix`
- `cmd_prefix: (assignment | redirect)+`
- `cmd_suffix: (arg | redirect)+`

This keeps extractor logic structural and avoids heuristic guessing.

## Target entities

Extractor emits `CommandRecord` with:

- `name`
- `args`
- `redirects`
- `assignments`
- `substitutions` (with stored `subtree` from sub-parser)
- `heredocs` (delimiter/body/quoted flags)
- `source_span`

## Notes

- Process substitution is parsed structurally via grammar rules (`< ( compound_list )`, `> ( compound_list )`), not regex nesting.
- Nested command substitutions are re-parsed through the recursive parser interface.
