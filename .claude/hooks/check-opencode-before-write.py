#!/usr/bin/env python3
"""
PreToolUse hook: Suggest OpenCode consultation for architecture files only.

Only fires when editing explicit architecture/design files (DESIGN.md, etc.),
not on routine source code edits.
"""

import json
import sys
from pathlib import Path

MAX_PATH_LENGTH = 4096
MAX_CONTENT_LENGTH = 1_000_000

# Only these files warrant an OpenCode consultation suggestion
ARCHITECTURE_FILES = [
    "DESIGN.md",
    "ARCHITECTURE.md",
    "design.md",
    "architecture.md",
]


def validate_input(file_path: str, content: str) -> bool:
    if not file_path or len(file_path) > MAX_PATH_LENGTH:
        return False
    if len(content) > MAX_CONTENT_LENGTH:
        return False
    if ".." in file_path:
        return False
    return True


def should_suggest_opencode(file_path: str) -> tuple[bool, str]:
    """Only suggest for explicit architecture/design files."""
    filename = Path(file_path).name
    if filename in ARCHITECTURE_FILES:
        return True, f"Editing architecture file '{filename}'"
    return False, ""


def main():
    try:
        data = json.load(sys.stdin)
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "") or tool_input.get("new_string", "")

        if not validate_input(file_path, content):
            sys.exit(0)

        should_suggest, reason = should_suggest_opencode(file_path)

        if should_suggest:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": (
                        f"[Design File Edit] {reason}. "
                        "Consider consulting OpenCode for architecture decisions."
                    ),
                }
            }
            print(json.dumps(output))

        sys.exit(0)

    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
