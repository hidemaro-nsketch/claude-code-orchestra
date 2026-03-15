#!/usr/bin/env python3
"""
PostToolUse hook: Suggest code review after large implementations.

Only fires once per session when 8+ source files or 500+ lines
have been modified. Significantly raised thresholds to avoid noise.
"""

import json
import os
import sys

MAX_PATH_LENGTH = 4096
MAX_CONTENT_LENGTH = 1_000_000

STATE_FILE = "/tmp/claude-code-implementation-state.json"

# Raised thresholds to avoid noise
MIN_FILES_FOR_REVIEW = 8
MIN_LINES_FOR_REVIEW = 500

SOURCE_EXTENSIONS = {".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs"}


def validate_input(file_path: str, content: str) -> bool:
    if not file_path or len(file_path) > MAX_PATH_LENGTH:
        return False
    if len(content) > MAX_CONTENT_LENGTH:
        return False
    if ".." in file_path:
        return False
    return True


def load_state() -> dict:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {"files_changed": [], "total_lines": 0, "review_suggested": False}


def save_state(state: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass


def count_lines(content: str) -> int:
    lines = content.split("\n")
    return len([l for l in lines if l.strip() and not l.strip().startswith("#")])


def main():
    try:
        data = json.load(sys.stdin)
        if data.get("tool_name") not in ["Write", "Edit"]:
            sys.exit(0)

        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "") or tool_input.get("new_string", "")

        if not validate_input(file_path, content):
            sys.exit(0)

        # Skip non-source files
        ext = os.path.splitext(file_path)[1]
        if ext not in SOURCE_EXTENSIONS:
            sys.exit(0)

        state = load_state()
        if file_path not in state["files_changed"]:
            state["files_changed"].append(file_path)
        state["total_lines"] += count_lines(content)
        save_state(state)

        # Only fire once per session
        if state.get("review_suggested"):
            sys.exit(0)

        files_count = len(state["files_changed"])
        total_lines = state["total_lines"]

        should_review = (
            files_count >= MIN_FILES_FOR_REVIEW or total_lines >= MIN_LINES_FOR_REVIEW
        )

        if should_review:
            state["review_suggested"] = True
            save_state(state)

            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"[Review Milestone] {files_count} files, {total_lines} lines modified. "
                        "Consider running /team-review for a structured review."
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
