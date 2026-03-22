from __future__ import annotations

import argparse
from time import perf_counter

from extractor import extract_commands
from parser import BashParser


def main() -> None:
    cli = argparse.ArgumentParser(description="Benchmark the minimal Bash parser.")
    cli.add_argument("path", help="Path to a shell script")
    cli.add_argument("--with-extractor", action="store_true", help="Also run the command extractor")
    args = cli.parse_args()

    parser = BashParser()
    parsed = parser.parse_file(args.path)
    print(f"Parse time: {parsed.elapsed_ms:.3f} ms")
    print(parsed.tree.pretty())

    if args.with_extractor:
        started = perf_counter()
        commands = extract_commands(parsed)
        elapsed_ms = (perf_counter() - started) * 1000
        print(f"Extractor time: {elapsed_ms:.3f} ms")
        print(f"Extracted commands: {len(commands)}")


if __name__ == "__main__":
    main()
