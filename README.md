# lark-bash

Bash parser Python library based on Lark (LALR) with an AST shape designed for static analysis.

## Install

```bash
pip install -e .
```

## Quick start

```python
from bash_lark import BashParser

parser = BashParser()
result = parser.parse("echo hello > /tmp/out")
for cmd in result.script.iter_commands():
    print(cmd.name.text if cmd.name else None, [arg.text for arg in cmd.args], [r.op for r in cmd.redirects])
```

## Benchmark / AST dump script

```bash
python scripts/parse_and_benchmark.py path/to/script.sh
```

It prints a JSON-like AST dump and elapsed parse time in milliseconds.

## Tests

Smoke tests pull examples from `tree-sitter-bash/examples` and parse them to ensure grammar stability:

```bash
pytest
```
