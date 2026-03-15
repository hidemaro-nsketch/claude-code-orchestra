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

DEPLOY_SKILL_TEMPLATE = (
    "Use `/deploy` skill for git operations. "
    "The deploy skill runs in `context: fork` and handles both "
    "deploy workflows (push + PR) and ad-hoc git operations (commit, log, diff, branch, etc.)."
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
            if category == "Git operation":
                context_msg = (
                    f"**Routing recommendation** [{category}]: "
                    "This git operation should be routed through the `/deploy` skill. "
                    f"{DEPLOY_SKILL_TEMPLATE} "
                    "Allowed directly without /deploy: `git status`, `git branch --show-current`, "
                    "`git rev-parse`, `git config --get`."
                )
            else:
                context_msg = (
                    f"**Routing recommendation** [{category}]: "
                    "Consider running this via a subagent for context isolation. "
                    "Use: Agent tool (subagent_type: 'general-purpose') with prompt describing the task. "
                    "Note: `context: fork` skills execute directly — this hook does not apply to them."
                )
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": context_msg,
                }
            }
            print(json.dumps(output))

        sys.exit(0)

    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
