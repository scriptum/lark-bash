from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extractor import extract_commands
from parser import BashParser


def main() -> None:
    cli = argparse.ArgumentParser(description="Debug parse tree and extracted command records.")
    cli.add_argument("path", help="Path to a shell script")
    args = cli.parse_args()

    parsed = BashParser().parse_file(args.path)
    print(parsed.tree.pretty())
    print(json.dumps([command.to_dict() for command in extract_commands(parsed)], indent=2))


if __name__ == "__main__":
    main()
