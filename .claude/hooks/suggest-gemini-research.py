#!/usr/bin/env python3
"""
PreToolUse hook: Suggest Gemini for deep external research only.

Only fires on WebSearch/WebFetch when the query involves comprehensive
library comparison or migration research. Simple lookups are ignored.
"""

import json
import sys

# Only these specific research topics warrant Gemini suggestion
DEEP_RESEARCH_INDICATORS = [
    "comparison",
    "migration guide",
    "breaking change",
    "api reference",
    "specification",
    "best practice",
]

SIMPLE_LOOKUP_PATTERNS = [
    "error message",
    "stack trace",
    "version",
    "release notes",
    "changelog",
    "how to",
    "example",
    "tutorial",
]


def should_suggest_gemini(query: str, url: str = "") -> tuple[bool, str]:
    combined = f"{query} {url}".lower()

    for pattern in SIMPLE_LOOKUP_PATTERNS:
        if pattern in combined:
            return False, ""

    for indicator in DEEP_RESEARCH_INDICATORS:
        if indicator in combined:
            return True, f"Research involves '{indicator}'"

    # Very long queries suggest complex research
    if len(query) > 200:
        return True, "Complex research query"

    return False, ""


def main():
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})

        query = ""
        url = ""
        if tool_name == "WebSearch":
            query = tool_input.get("query", "")
        elif tool_name == "WebFetch":
            url = tool_input.get("url", "")
            query = tool_input.get("prompt", "")

        should_suggest, reason = should_suggest_gemini(query, url)

        if should_suggest:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": (
                        f"[Gemini Research] {reason}. "
                        "Consider using Gemini CLI for comprehensive research. "
                        "Use subagent to save results to .claude/docs/research/."
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
