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
    commands = extract_commands(parsed)

    print("=== Parse Tree ===")
    print(parsed.tree.pretty())
    print("=== Commands ===")
    print(json.dumps([command.to_dict() for command in commands], indent=2))
    print("=== Word Parts ===")
    word_parts = [
        {
            "command_id": command.command_id,
            "name": command.name,
            "args_structured": [[part.to_dict() for part in arg] for arg in command.args_structured],
            "args_expanded": [[record.to_dict() for record in arg] for arg in command.args_expanded],
        }
        for command in commands
    ]
    print(json.dumps(word_parts, indent=2))
    print("=== Subparses ===")
    print(
        json.dumps(
            [
                {
                    "command_id": command.command_id,
                    "name": command.name,
                    "subparses": [record.to_dict() for record in command.subparses],
                }
                for command in commands
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
