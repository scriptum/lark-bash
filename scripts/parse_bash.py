#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from pathlib import Path

from lark_bash import BashParser


def main() -> None:
    ap = argparse.ArgumentParser(description="Parse bash script and print Lark tree")
    ap.add_argument("path", type=Path)
    args = ap.parse_args()

    text = args.path.read_text(encoding="utf-8")
    parser = BashParser()

    started = time.perf_counter()
    tree = parser.parse(text)
    elapsed_ms = (time.perf_counter() - started) * 1000

    print(tree.pretty())
    print(f"Parse time: {elapsed_ms:.2f} ms")


if __name__ == "__main__":
    main()
