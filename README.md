# lark-bash

Bash parser Python library based on Lark.

## Layout

- `grammar/` — main and nested grammars
- `src/lark_bash/` — parser/extractor library
- `scripts/` — CLI helpers for parse tree and command extraction
- `tests/` — parser and extractor smoke tests
- `examples/` — sample shell scripts
- `docs/` — references and design docs

## Quickstart

```bash
python -m pip install -e .
python scripts/parse_bash.py examples/install.sh
python scripts/extract_commands.py examples/install.sh
```
