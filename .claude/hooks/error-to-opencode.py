#!/usr/bin/env python3
"""
PostToolUse hook: Suggest opencode-debugger for significant errors only.

Only fires when 3+ distinct error patterns are found, indicating a
complex issue worth debugging with OpenCode. Single errors and
trivial failures are ignored.
"""

import json
import re
import sys

ERROR_PATTERNS = [
    r"Traceback \(most recent call last\)",
    r"(?:TypeError|ValueError|AttributeError|ImportError|KeyError|IndexError|RuntimeError)",
    r"(?:SyntaxError|NameError|FileNotFoundError|PermissionError|OSError)",
    r"panic:",
    r"segmentation fault",
    r"core dumped",
    r"npm ERR!",
    r"cargo error",
]

# Minimum distinct patterns to trigger suggestion
MIN_PATTERNS_FOR_SUGGESTION = 3

IGNORE_COMMANDS = [
    "git ",
    "ls",
    "pwd",
    "cat",
    "head",
    "tail",
    "echo",
    "which",
    "type",
    "true",
    "opencode ",
    "gemini ",
]

IGNORE_OUTPUTS = [
    "command not found",
    "No such file or directory",
    "already exists",
    "nothing to commit",
    "Already up to date",
    "Everything up-to-date",
]

MIN_OUTPUT_LENGTH = 50


def should_ignore(command: str, output: str) -> bool:
    cmd = command.strip()
    for ignore in IGNORE_COMMANDS:
        if cmd.startswith(ignore):
            return True
    for ignore in IGNORE_OUTPUTS:
        if ignore in output and output.count("\n") < 5:
            return True
    return False


def detect_errors(output: str) -> int:
    """Count distinct error patterns found."""
    count = 0
    for pattern in ERROR_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            count += 1
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

        if not command or len(tool_output) < MIN_OUTPUT_LENGTH:
            sys.exit(0)

        if should_ignore(command, tool_output):
            sys.exit(0)

        error_count = detect_errors(tool_output)

        if error_count >= MIN_PATTERNS_FOR_SUGGESTION:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"[Error Detected] {error_count} distinct error patterns found. "
                        "Consider using `opencode-debugger` subagent for analysis."
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
