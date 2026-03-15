#!/usr/bin/env python3
"""
PostToolUse hook: Suggest debugging for complex test/build failures.

Only fires for test/build commands with 5+ failure patterns,
complementing error-to-opencode.py (which handles general errors).
"""

import json
import re
import sys

TEST_BUILD_COMMANDS = [
    "pytest",
    "npm test",
    "npm run test",
    "npm run build",
    "uv run pytest",
    "ruff check",
    "ty check",
    "mypy",
    "tsc",
    "cargo test",
    "go test",
    "make test",
    "make build",
]

FAILURE_PATTERNS = [
    r"FAILED",
    r"Error:",
    r"error\[",
    r"AssertionError",
    r"TypeError",
    r"ValueError",
    r"AttributeError",
    r"ImportError",
    r"SyntaxError",
    r"Traceback",
    r"panic:",
    r"FAIL:",
]

# Require significant failures
MIN_FAILURES = 5

SIMPLE_ERRORS = [
    "ModuleNotFoundError",
    "command not found",
    "No such file or directory",
]


def is_test_or_build_command(command: str) -> bool:
    command_lower = command.lower()
    return any(cmd in command_lower for cmd in TEST_BUILD_COMMANDS)


def count_failures(output: str) -> int:
    # Skip simple errors
    for simple in SIMPLE_ERRORS:
        if simple in output:
            return 0

    count = 0
    for pattern in FAILURE_PATTERNS:
        matches = re.findall(pattern, output, re.IGNORECASE)
        count += len(matches)
    return count


def main():
    try:
        data = json.load(sys.stdin)
        if data.get("tool_name") != "Bash":
            sys.exit(0)

        tool_input = data.get("tool_input", {})
        tool_response = data.get("tool_response", {})
        command = tool_input.get("command", "")
        tool_output = tool_response.get("stdout", "") or tool_response.get(
            "content", ""
        )

        if not is_test_or_build_command(command):
            sys.exit(0)

        failure_count = count_failures(tool_output)

        if failure_count >= MIN_FAILURES:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"[Test/Build Failures] {failure_count} failure patterns detected. "
                        "Consider using `opencode-debugger` subagent for systematic analysis."
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
