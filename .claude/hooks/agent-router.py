#!/usr/bin/env python3
"""
UserPromptSubmit hook: Unified intent router for skills and agents.

Routes user prompts to the appropriate skill or agent:
1. If an explicit skill command (/startproject, /team-implement, etc.) is present, do nothing.
2. Detect skill intent (startproject, team-implement, team-review, deploy).
3. Detect agent intent (OpenCode, Gemini).
4. Exclude lightweight tasks (questions, single-file edits, explanations).

Output: additionalContext suggesting the best action (soft recommendation, not forced).

Priority: explicit command > skill intent > agent intent > none
"""

import json
import re
import sys

# ---------------------------------------------------------------------------
# Skill intent triggers
# ---------------------------------------------------------------------------

STARTPROJECT_TRIGGERS = {
    "ja": [
        "新機能を",
        "新しい機能",
        "機能を作",
        "機能を開発",
        "機能を実装したい",
        "プロジェクトを始",
        "プロジェクト開始",
        "計画して",
        "計画を立てて",
        "設計から始",
        "要件定義",
        "要件を整理",
        "新規開発",
        "featureを始",
        "featureを進",
        "開発を始めたい",
        "作りたい",
        "つくりたい",
        "構築したい",
        "実装したい",
        "issue #",
        "issueを実行",
        "issueを進",
        "チケットを進",
        "チケットを実行",
        "タスクを始",
        "タスクを進",
        "githubの#",
        "githubの #",
    ],
    "en": [
        "start project",
        "start a project",
        "start new feature",
        "plan this feature",
        "plan the feature",
        "begin development",
        "kick off",
        "start building",
        "new feature",
        "implement issue",
        "work on issue",
        "execute issue",
    ],
}

TEAM_IMPLEMENT_TRIGGERS = {
    "ja": [
        "実装して",
        "実装を開始",
        "実装に進",
        "実装を始",
        "実装フェーズ",
        "コードを書いて",
        "この計画で実装",
        "承認した",
        "承認します",
        "進めて",
        "計画通りに",
        "計画で進めて",
        "実装に入",
        "コーディング",
    ],
    "en": [
        "implement this",
        "start implementing",
        "begin implementation",
        "approved, implement",
        "go ahead and implement",
        "proceed with implementation",
        "code this up",
        "start coding",
    ],
}

TEAM_REVIEW_TRIGGERS = {
    "ja": [
        "レビューして",
        "レビューを",
        "コードレビュー",
        "差分レビュー",
        "実装のレビュー",
        "品質チェック",
        "セキュリティチェック",
        "実装が終わった",
        "実装完了",
        "レビューに進",
        "チェックして",
    ],
    "en": [
        "review this",
        "code review",
        "review the implementation",
        "review the code",
        "check the implementation",
        "quality review",
        "security review",
        "implementation is done",
        "ready for review",
    ],
}

DEPLOY_TRIGGERS = {
    "ja": [
        "デプロイ",
        "prを作",
        "pr作成",
        "pushして",
        "プッシュして",
        "マージ",
        "リリース",
        "本番に",
        "ブランチをpush",
        "prを出",
        "コミットして",
        "コミットを作",
        "ブランチを切",
        "ブランチを作",
        "ブランチを変",
        "チェックアウト",
        "git log",
        "git diff",
        "git show",
        "git blame",
        "git stash",
        "git rebase",
        "差分を見",
        "差分を表示",
        "履歴を見",
        "履歴を表示",
        "履歴を調べ",
        "ログを見",
        "ログを表示",
        "blameして",
        "stashして",
        "pullして",
        "fetchして",
        "タグを",
        "cherry-pick",
    ],
    "en": [
        "deploy",
        "create pr",
        "create a pr",
        "create pull request",
        "push to remote",
        "push the branch",
        "merge this",
        "release this",
        "ship it",
        "send pr",
        "commit this",
        "commit the",
        "make a commit",
        "create branch",
        "switch branch",
        "checkout",
        "git log",
        "git diff",
        "git show",
        "git blame",
        "git stash",
        "git rebase",
        "show diff",
        "show the diff",
        "show log",
        "show history",
        "git pull",
        "git fetch",
        "git tag",
        "cherry-pick",
    ],
}

# ---------------------------------------------------------------------------
# Agent intent triggers (preserved from original)
# ---------------------------------------------------------------------------

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

GEMINI_TRIGGERS = {
    "ja": [
        "調べて",
        "リサーチして",
        "調査して",
        "pdf",
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

# ---------------------------------------------------------------------------
# Lightweight task exclusion patterns
# ---------------------------------------------------------------------------

# Patterns that indicate a question or explanation request (not a skill invocation).
# These are checked ONLY when no strong skill trigger is found, to avoid
# false negatives on prompts like "新機能を作りたい" which contain "作りたい".
QUESTION_PATTERNS = {
    "ja": [
        "とは何",
        "って何",
        "ってなに",
        "を教えて",
        "を説明して",
        "の意味は",
        "の違いは",
        "はどういう",
        "なぜ失敗",
        "なぜ動かない",
        "どうして",
        "見せて",
        "表示して",
    ],
    "en": [
        "what is",
        "what are",
        "how does",
        "how do",
        "why does",
        "why is",
        "explain",
        "show me",
        "display",
        "can you tell",
        "tell me about",
        "describe",
    ],
}

# Single-file or lightweight operations that should NOT trigger a workflow skill.
# Only used as a secondary filter (skill triggers always win).
# NOTE: Git operations (commit, push, branch, etc.) are intentionally excluded
# from this list because they are routed to /deploy skill (Ad-hoc Git mode).
LIGHTWEIGHT_OPERATION_PATTERNS = {
    "ja": [
        "直して",
        "リネームして",
        "フォーマットして",
        "lintして",
        "テストを実行して",
    ],
    "en": [
        "fix this typo",
        "rename this",
        "format this",
        "run lint",
        "run test",
        "run the test",
    ],
}

# Explicit skill command pattern (user already typed the skill name)
EXPLICIT_SKILL_RE = re.compile(
    r"^/(?:startproject|team-implement|team-review|deploy)\b", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Detection logic
# ---------------------------------------------------------------------------


def has_explicit_skill(prompt: str) -> bool:
    """Check if the prompt already contains an explicit skill command."""
    return bool(EXPLICIT_SKILL_RE.search(prompt.strip()))


def is_lightweight_task(prompt: str, has_skill_trigger: bool = False) -> bool:
    """Check if the prompt is a lightweight task that should not trigger a skill.

    If a strong skill trigger was already found, we skip suppression entirely --
    the user's intent to invoke a skill takes precedence.
    """
    # If we already found a strong skill trigger, don't suppress
    if has_skill_trigger:
        return False

    prompt_lower = prompt.lower()

    # Question patterns suppress skill routing
    for patterns in QUESTION_PATTERNS.values():
        for pattern in patterns:
            if pattern in prompt_lower:
                return True

    # Lightweight operations suppress skill routing
    for patterns in LIGHTWEIGHT_OPERATION_PATTERNS.values():
        for pattern in patterns:
            if pattern in prompt_lower:
                return True

    return False


def detect_skill_intent(prompt: str) -> tuple[str | None, str]:
    """Detect which skill the user likely wants to invoke.

    Returns (skill_name, matched_trigger) or (None, "").
    """
    prompt_lower = prompt.lower()

    skill_candidates = [
        ("startproject", STARTPROJECT_TRIGGERS),
        ("team-implement", TEAM_IMPLEMENT_TRIGGERS),
        ("team-review", TEAM_REVIEW_TRIGGERS),
        ("deploy", DEPLOY_TRIGGERS),
    ]

    for skill_name, triggers in skill_candidates:
        for lang_triggers in triggers.values():
            for trigger in lang_triggers:
                if trigger in prompt_lower:
                    return skill_name, trigger

    return None, ""


def detect_agent_intent(prompt: str) -> tuple[str | None, str]:
    """Detect which agent should handle this prompt (OpenCode or Gemini)."""
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


# ---------------------------------------------------------------------------
# Skill descriptions for additionalContext
# ---------------------------------------------------------------------------

SKILL_DESCRIPTIONS = {
    "startproject": (
        "[Skill Routing] Detected project/feature start intent (trigger: '{trigger}'). "
        "This looks like a new feature or project task. "
        "Use `/startproject` skill to begin the planning workflow: "
        "codebase analysis, requirements gathering, design, and implementation planning. "
        "Run: /startproject {prompt_summary}"
    ),
    "team-implement": (
        "[Skill Routing] Detected implementation intent (trigger: '{trigger}'). "
        "This looks like a request to implement an approved plan. "
        "Use `/team-implement` skill for parallel implementation with Agent Teams. "
        "Run: /team-implement"
    ),
    "team-review": (
        "[Skill Routing] Detected review intent (trigger: '{trigger}'). "
        "This looks like a request to review implemented code. "
        "Use `/team-review` skill for parallel code review with specialized reviewers. "
        "Run: /team-review"
    ),
    "deploy": (
        "[Skill Routing] Detected git/deploy intent (trigger: '{trigger}'). "
        "This looks like a git operation request. "
        "Use `/deploy` skill which handles both deploy workflows (push + PR) "
        "and ad-hoc git operations (commit, log, diff, branch, etc.) in a context-isolated fork. "
        "Run: /deploy"
    ),
}


# ---------------------------------------------------------------------------
# Main routing logic
# ---------------------------------------------------------------------------


def route_prompt(prompt: str) -> dict | None:
    """Route the prompt to the best skill or agent.

    Returns a hookSpecificOutput dict or None if no routing is needed.
    """
    # 1. If user already typed an explicit skill command, do nothing
    if has_explicit_skill(prompt):
        return None

    # 2. Check for skill intent (highest priority for non-lightweight tasks)
    skill, trigger = detect_skill_intent(prompt)
    if skill and not is_lightweight_task(prompt, has_skill_trigger=True):
        # Build a short summary of the prompt for the skill argument
        prompt_summary = prompt.strip()[:80]
        if len(prompt.strip()) > 80:
            prompt_summary += "..."

        context_msg = SKILL_DESCRIPTIONS[skill].format(
            trigger=trigger,
            prompt_summary=prompt_summary,
        )
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context_msg,
            }
        }

    # 3. Check for agent intent (OpenCode / Gemini)
    agent, trigger = detect_agent_intent(prompt)
    if agent == "opencode":
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    f"[Agent Routing] Detected '{trigger}' - consider using "
                    "OpenCode CLI for deep reasoning. "
                    "Use subagent for context isolation."
                ),
            }
        }
    elif agent == "gemini":
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    f"[Agent Routing] Detected '{trigger}' - consider using "
                    "Gemini CLI for external research or multimodal processing. "
                    "Use subagent for context isolation."
                ),
            }
        }

    # 4. No routing needed
    return None


def main():
    try:
        data = json.load(sys.stdin)
        prompt = data.get("prompt", "")

        # Skip empty or trivially short prompts
        if len(prompt) < 5:
            sys.exit(0)

        result = route_prompt(prompt)
        if result:
            print(json.dumps(result))

        sys.exit(0)

    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
