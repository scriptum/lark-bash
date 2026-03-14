#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass

from bash_lark import BashParser


def to_jsonable(value):
    if is_dataclass(value):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse bash file with Lark and print AST + timing")
    parser.add_argument("script", help="Path to bash script")
    args = parser.parse_args()

    with open(args.script, "r", encoding="utf-8") as fh:
        source = fh.read()

    bash_parser = BashParser()
    result = bash_parser.parse(source)

    print(json.dumps(to_jsonable(result.script), ensure_ascii=False, indent=2))
    print(f"elapsed_ms={result.elapsed_ms:.3f}")
    print(f"commands={sum(1 for _ in result.script.iter_commands())}")
    print(f"heredocs={len(result.script.here_docs)}")


if __name__ == "__main__":
    main()
