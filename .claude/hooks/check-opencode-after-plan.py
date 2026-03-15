#!/usr/bin/env python3
"""
PostToolUse hook: Suggest OpenCode review after Plan agent tasks only.

Only fires when the Plan subagent type is used explicitly.
Does not fire on general task keywords.
"""

import json
import sys


def main():
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("tool_name", "")

        if tool_name != "Task":
            sys.exit(0)

        tool_input = data.get("tool_input", {})
        subagent_type = tool_input.get("subagent_type", "").lower()

        # Only fire for explicit Plan agent
        if subagent_type == "plan":
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        "[Plan Review] Plan task completed. "
                        "Consider having OpenCode review the plan if it involves "
                        "significant architecture decisions."
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
