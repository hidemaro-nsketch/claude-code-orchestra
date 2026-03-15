#!/usr/bin/env python3
"""
PreToolUse hook: Recommend subagent routing for operational commands.

For ad-hoc Bash commands (git, docker, ruff, uv), recommends executing
via a subagent for context isolation. Skills with `context: fork`
(startproject, team-implement, team-review, deploy) bypass this hook
entirely and execute commands directly.

NOTE: Uses additionalContext (soft recommendation), not decision:block.
"""

import json
import re
import sys

# Git subcommands that are ALLOWED directly (informational / read-only)
ALLOWED_GIT_PATTERNS = [
    re.compile(r"^git\s+status\b"),
    re.compile(r"^git\s+branch\s+--show-current\b"),
    re.compile(r"^git\s+rev-parse\b"),
    re.compile(r"^git\s+config\s+--get\b"),
    re.compile(r"^git\s+remote\s+-v\b"),
]

# Other commands recommended for subagent routing
ROUTED_COMMAND_PATTERNS = [
    (re.compile(r"^docker(?:\s|-)"), "Docker operation"),
    (re.compile(r"^docker-compose\b"), "Docker operation"),
    (
        re.compile(r"^(?:uv\s+run\s+)?ruff\s+(?:check|format)\b"),
        "Lint/format",
    ),
    (re.compile(r"^uv\s+(?:add|remove|sync|lock)\b"), "Dependency management"),
]

SUBAGENT_TEMPLATE = (
    "Agent tool (subagent_type: 'general-purpose') with prompt describing the task. "
    "The subagent executes commands directly (no Gemini needed)."
)


def is_git_command(command: str) -> bool:
    """Check if the command is a git command."""
    return bool(re.search(r"\bgit\s+\w+", command))


def is_allowed_git(command: str) -> bool:
    """Check if this git command is in the allowed list."""
    cmd_stripped = command.strip()
    for pattern in ALLOWED_GIT_PATTERNS:
        if pattern.search(cmd_stripped):
            return True
    return False


def check_routed_command(command: str) -> tuple[bool, str]:
    """Check if this command matches a routed pattern (non-git)."""
    cmd_stripped = command.strip()
    for pattern, category in ROUTED_COMMAND_PATTERNS:
        if pattern.search(cmd_stripped):
            return True, category
    return False, ""


def analyze_command(command: str) -> tuple[bool, str]:
    """Analyze a bash command for routing recommendations.

    Returns: (should_recommend, category)
    """
    cmd_stripped = command.strip()

    # Check for git commands
    if is_git_command(cmd_stripped):
        if is_allowed_git(cmd_stripped):
            return False, ""
        return True, "Git operation"

    # Check for other routed commands
    is_routed, category = check_routed_command(cmd_stripped)
    if is_routed:
        return True, category

    return False, ""


def main():
    try:
        data = json.load(sys.stdin)
        tool_input = data.get("tool_input", {})
        command = tool_input.get("command", "")

        if not command:
            sys.exit(0)

        should_recommend, category = analyze_command(command)

        if should_recommend:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": (
                        f"**Routing recommendation** [{category}]: "
                        "Consider running this via a subagent for context isolation. "
                        f"Use: {SUBAGENT_TEMPLATE} "
                        "Note: `context: fork` skills (startproject, team-implement, "
                        "team-review, deploy) execute directly — this hook does not apply to them. "
                        "Allowed directly: `git status`, `git branch --show-current`, "
                        "`git rev-parse`, `git config --get`."
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
