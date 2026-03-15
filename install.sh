#!/usr/bin/env bash
set -euo pipefail

# Install workflow skills (startproject, team-implement, team-review, deploy)
# and their dependencies (hooks, rules, related skills) to ~/.claude/

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/.claude"
TARGET_DIR="$HOME/.claude"

FILES=(
  # Skills: core workflow
  skills/startproject/SKILL.md
  skills/startproject/references/task-patterns.md
  skills/team-implement/SKILL.md
  skills/team-review/SKILL.md
  skills/deploy/SKILL.md

  # Skills: dependencies
  skills/design-tracker/SKILL.md
  skills/simplify/SKILL.md

  # Hooks
  hooks/agent-router.py

  # Rules: workflow
  rules/skill-auto-routing.md
  rules/adaptive-execution.md
  rules/tool-routing.md

  # Rules: referenced by reviewers
  rules/security.md
  rules/coding-principles.md
  rules/testing.md
)

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Error: $SOURCE_DIR not found" >&2
  exit 1
fi

for file in "${FILES[@]}"; do
  src="$SOURCE_DIR/$file"
  dest="$TARGET_DIR/$file"

  if [[ ! -f "$src" ]]; then
    echo "  SKIP (not found): $file"
    continue
  fi

  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  echo "  $file"
done

echo "Done. Copied ${#FILES[@]} files to $TARGET_DIR"
