#!/usr/bin/env python3
"""
UserPromptSubmit hook: Route to appropriate agent based on user intent.

Suggests OpenCode for explicit design/debug consultation requests,
and Gemini for external research and multimodal tasks only.
Narrowed triggers to avoid noise on routine tasks.
"""

import json
import sys

# Triggers for OpenCode — only explicit consultation requests
OPENCODE_TRIGGERS = {
    "ja": [
        "設計相談",
        "どう設計すべき",
        "アーキテクチャ相談",
        "デバッグして",
        "原因を分析",
        "トレードオフ",
        "比較検討",
        "深く考えて",
        "second opinion",
    ],
    "en": [
        "design consultation",
        "think deeper",
        "consult opencode",
        "second opinion",
        "trade-off analysis",
        "debug this",
    ],
}

# Triggers for Gemini — external research and multimodal only
GEMINI_TRIGGERS = {
    "ja": [
        "調べて",
        "リサーチして",
        "調査して",
        "PDF",
        "動画を",
        "音声を",
        "コードベース全体",
        "横断的に",
    ],
    "en": [
        "research this",
        "investigate",
        "look up",
        "analyze this pdf",
        "analyze this video",
        "analyze this audio",
        "entire codebase",
    ],
}


def detect_agent(prompt: str) -> tuple[str | None, str]:
    """Detect which agent should handle this prompt."""
    prompt_lower = prompt.lower()

    for triggers in OPENCODE_TRIGGERS.values():
        for trigger in triggers:
            if trigger in prompt_lower:
                return "opencode", trigger

    for triggers in GEMINI_TRIGGERS.values():
        for trigger in triggers:
            if trigger in prompt_lower:
                return "gemini", trigger

    return None, ""


def main():
    try:
        data = json.load(sys.stdin)
        prompt = data.get("prompt", "")

        if len(prompt) < 15:
            sys.exit(0)

        agent, trigger = detect_agent(prompt)

        if agent == "opencode":
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        f"[Agent Routing] Detected '{trigger}' - consider using "
                        "OpenCode CLI for deep reasoning. "
                        "Use subagent for context isolation."
                    ),
                }
            }
            print(json.dumps(output))

        elif agent == "gemini":
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        f"[Agent Routing] Detected '{trigger}' - consider using "
                        "Gemini CLI for external research or multimodal processing. "
                        "Use subagent for context isolation."
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
