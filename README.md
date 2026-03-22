# lark-bash

`lark-bash` is an iterative Bash/POSIX shell parser prototype built on top of pure Python and Lark.

## Design goals

The current implementation intentionally fixes the architecture before chasing full Bash compatibility:

- **Primary grammar source:** the prototype is based on the POSIX shell references in `docs/POSIX-Shell.ebnf.txt` and `docs/Posix Shell Commad Language.md`.
- **Parsing output:** the parser always returns a **Lark parse tree**.
- **Post-processing layers:**
  - a **Visitor** extracts SAST-oriented entities from the tree;
  - a dedicated **sub-parser manager** spins up separate Lark parser instances for nested command substitutions, process substitutions, backticks, and simple here-doc bodies;
  - future **Transformer** passes can extend the same architecture for arithmetic expansion and other ambiguous Bash-only contexts.
- **No handwritten recursive descent over raw source:** all syntax recognition must go through Lark grammars.

## Target entities for SAST

The parse tree and extractor are designed around the following node families:

| Entity | How it is identified in the current tree/extractor |
| --- | --- |
| `command` | `simple_command` nodes with at least one word, assignment, or redirect |
| `args` | `word` children after the first command word |
| `redirects` | `redirect` nodes carrying optional FD, operator, and target |
| `assignment` | `assignment` nodes that appear before or around simple commands |
| `function_def` | Reserved for a later grammar extension |
| `keyword` | Reserved for contextual lexer / reserved-word-aware grammar stage |
| `substitution` | `subparsers.py` extracts `$()`, backticks and process substitution payloads into nested parse trees and nested command records |
| `heredoc` | simple `<<` / `<<-` bodies are pre-isolated, then parsed by a dedicated nested Lark instance when expansion is enabled |

## Current repository layout

- `grammar/` — Lark grammars.
- `parser.py` — parser API and CLI entrypoint.
- `extractor.py` — `Visitor`-based command extraction layer.
- `scripts/debug_extract.py` — debug utility that prints the tree and extracted command records.
- `benchmark.py` — parse/extraction benchmark helper.
- `tests/` — parser and extractor smoke tests.
- `examples/` — real shell scripts used as parse corpus.
- `docs/` — POSIX and Lark notes used to shape the design.

## Implemented scope

The initial LALR parser covers:

- simple commands and assignment-prefixed commands;
- separators with newlines, `;`, `&`, plus boolean command lists with `&&` and `||`;
- pipelines with optional leading `!`;
- redirects from the POSIX-core set (`<`, `>`, `>|`, `>>`, `<<`, `<<-`, `<&`, `>&`, `<>`);
- grouped commands with `{ ... }` and `( ... )`;
- POSIX compound commands: `if`, `elif`, `else`, `while`, `until`, `for`, `case`, and `fname() compound-command` function definitions;
- nested sub-parsing for `$()`, backticks, `<(...)`, `>(...)`, and simple expansion-enabled here-doc bodies;
- blank lines, comments, trailing separators, trailing whitespace, escaped newlines, and files without a final newline.

This is still an **iterative POSIX-core stage** rather than a full Bash grammar: arithmetic expansion sub-grammars, rich here-doc quoting rules, `[[ ... ]]`, `(( ... ))`, arrays, `function name { ... }`, `select`, and other Bash-specific extensions are still planned work.

## Usage

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Parse a file and print the tree:

```bash
python parser.py examples/minimal.sh
```

Extract command records:

```bash
python scripts/debug_extract.py examples/minimal.sh
```

Run the benchmark smoke test:

```bash
python benchmark.py examples/minimal.sh --with-extractor
```

Run tests:

```bash
pytest
```
