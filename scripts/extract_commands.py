#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from lark_bash import BashParser, extract_commands


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract command records from bash file")
    ap.add_argument("path", type=Path)
    args = ap.parse_args()

    parser = BashParser()
    parsed = parser.parse_with_metadata(args.path.read_text(encoding="utf-8"))
    records = extract_commands(parsed.tree, source=parsed.source, heredocs=parsed.heredocs)

    for i, rec in enumerate(records, start=1):
        print(f"[{i}] name={rec.name!r}")
        print(f"    args={rec.args}")
        print(f"    redirects={rec.redirects}")
        print(f"    assignments={rec.assignments}")
        print(f"    substitutions={[s.raw for s in rec.substitutions]}")
        print(f"    heredocs={[(h.delimiter, h.quoted) for h in rec.heredocs]}")
        print(f"    span={rec.source_span}")


if __name__ == "__main__":
    main()
