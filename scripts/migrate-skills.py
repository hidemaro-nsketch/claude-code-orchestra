#!/usr/bin/env python3
"""Interactive CLI tool to migrate skills/rules to target repositories.

Uses fzf for interactive selection of phases and target repositories.
Follows the migration plan defined in docs/skill-migration-plan.md.

Usage:
    python scripts/migrate-skills.py                          # Interactive mode
    python scripts/migrate-skills.py --dry-run                # Preview only
    python scripts/migrate-skills.py --phase 0 --target /path # Non-interactive
    python scripts/migrate-skills.py --phase 0,1,2 --target . # Multiple phases
    python scripts/migrate-skills.py --force                  # Overwrite existing
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent.parent

DESIGN_TEMPLATE = """\
# Design Document

## Overview

## Architecture

## Implementation Plan

## TODO

## Open Questions

## Changelog
"""

CLAUDE_MD_SNIPPETS: dict[int, str] = {
    0: """\
## Rules & Standards

Coding standards enforced via `.claude/rules/`:

| Rule | Content |
|------|---------|
| `language.md` | English code, Japanese communication |
| `coding-principles.md` | Simplicity, single responsibility, early return |
| `testing.md` | TDD, AAA pattern, 80%+ coverage |
| `security.md` | Input validation, secrets management |

PostToolUse hook: auto lint/format on file changes.
""",
    1: """\
## Skills

| Command | Description |
|---------|-------------|
| `/plan` | Step-by-step implementation planning |
| `/tdd` | Test-Driven Development workflow |
| `/simplify` | Code simplification |
| `/design-tracker` | Track design decisions automatically |
| `/update-design` | Update design document |

Design decisions: `.claude/docs/DESIGN.md`
""",
    2: """\
## Documentation Management

| Command | Description |
|---------|-------------|
| `/research-lib` | Research libraries and save findings |
| `/update-lib-docs` | Update library constraint docs |

Library docs: `.claude/docs/libraries/`
""",
    3: """\
## Multi-Agent Collaboration

| Agent | Strength | Use For |
|-------|----------|---------|
| **Claude Code** | 1M context, orchestration | Codebase analysis, implementation |
| **Codex CLI** | Deep reasoning | Design decisions, debugging, trade-offs |
| **Gemini CLI** | Google Search, multimodal | External research, PDF/video/audio |

### When to Use

- **Design/debug** → Codex (`/codex-system`)
- **External research** → Gemini (`/gemini-system`)
- **Codebase analysis** → Gemini subagent (`gemini-explore`)

### Context Management

| Output Size | Method |
|-------------|--------|
| Short (~50 lines) | Direct call OK |
| Large (50+ lines) | Via subagent |
| Reports | Subagent → save to `.claude/docs/` |

→ `.claude/rules/codex-delegation.md`, `.claude/rules/gemini-delegation.md`, `.claude/rules/tool-routing.md`
""",
    4: """\
## Workflow

```
/startproject <feature>     Understand → Research & Design → Plan
    ↓ approval
/team-implement             Parallel implementation (Agent Teams)
    ↓ completion
/team-review                Parallel review (Agent Teams)
    ↓ completion
/deploy                     Push feature branch & return to original branch
```

| Command | Description |
|---------|-------------|
| `/startproject` | Multi-agent project initialization |
| `/team-implement` | Parallel implementation with Agent Teams |
| `/team-review` | Parallel code review with Agent Teams |
| `/deploy` | Push feature branch, return to original branch |
""",
    5: """\
## Session Management

| Command | Description |
|---------|-------------|
| `/checkpointing` | Save session context and learnings |
| `/init` | Initialize project settings |

Checkpoints: `.claude/checkpoints/` | Logs: `.claude/logs/`
""",
}

PHASES: dict[int, dict] = {
    0: {
        "name": "Foundation Rules",
        "description": "Base rules referenced by all skills",
        "files": [
            ".claude/rules/language.md",
            ".claude/rules/coding-principles.md",
            ".claude/rules/testing.md",
            ".claude/rules/security.md",
            ".claude/rules/dev-environment.md",
            ".claude/hooks/lint-on-save.py",
        ],
        "settings_hooks": [
            {
                "event": "PostToolUse",
                "matcher": "Edit|Write",
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/lint-on-save.py"',
                "timeout": 30,
            },
        ],
    },
    1: {
        "name": "Standalone Skills",
        "description": "Skills with no external CLI dependency",
        "files": [
            ".claude/skills/plan/SKILL.md",
            ".claude/skills/tdd/SKILL.md",
            ".claude/skills/simplify/SKILL.md",
            ".claude/skills/design-tracker/SKILL.md",
            ".claude/skills/update-design/SKILL.md",
        ],
        "templates": {
            ".claude/docs/DESIGN.md": DESIGN_TEMPLATE,
        },
    },
    2: {
        "name": "Documentation Skills",
        "description": "Library research and documentation management",
        "files": [
            ".claude/skills/research-lib/SKILL.md",
            ".claude/skills/update-lib-docs/SKILL.md",
        ],
        "dirs": [".claude/docs/libraries/"],
    },
    3: {
        "name": "External CLI Integration",
        "description": "Codex CLI + Gemini CLI skills (requires CLI installation)",
        "files": [
            ".claude/rules/codex-delegation.md",
            ".claude/rules/gemini-delegation.md",
            ".claude/rules/tool-routing.md",
            ".claude/skills/codex-system/SKILL.md",
            ".claude/skills/codex-system/references/agent-prompts.md",
            ".claude/skills/codex-system/references/code-review-task.md",
            ".claude/skills/codex-system/references/delegation-patterns.md",
            ".claude/skills/codex-system/references/refactoring-task.md",
            ".claude/skills/codex-system/references/troubleshooting.md",
            ".claude/skills/gemini-system/SKILL.md",
            ".claude/skills/gemini-system/references/lib-research-task.md",
            ".claude/skills/gemini-system/references/use-cases.md",
            ".claude/hooks/agent-router.py",
            ".claude/hooks/check-codex-before-write.py",
            ".claude/hooks/check-codex-after-plan.py",
            ".claude/hooks/error-to-codex.py",
            ".claude/hooks/enforce-tool-routing.py",
            ".claude/hooks/suggest-gemini-research.py",
            ".claude/hooks/log-cli-tools.py",
            ".claude/hooks/post-test-analysis.py",
            ".claude/hooks/post-implementation-review.py",
            ".claude/agents/general-purpose.md",
            ".claude/agents/codex-debugger.md",
            ".claude/agents/gemini-explore.md",
        ],
        "dirs": [".claude/docs/research/"],
        "settings_permissions": [
            "Bash(codex:*)",
            "Bash(gemini:*)",
        ],
        "settings_hooks": [
            {
                "event": "UserPromptSubmit",
                "matcher": "",
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/agent-router.py"',
                "timeout": 5,
            },
            {
                "event": "PreToolUse",
                "matcher": "Edit|Write",
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/check-codex-before-write.py"',
                "timeout": 10,
            },
            {
                "event": "PreToolUse",
                "matcher": "Bash",
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/enforce-tool-routing.py"',
                "timeout": 5,
            },
            {
                "event": "PreToolUse",
                "matcher": "WebSearch|WebFetch",
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/suggest-gemini-research.py"',
                "timeout": 5,
            },
            {
                "event": "PostToolUse",
                "matcher": "Task",
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/check-codex-after-plan.py"',
                "timeout": 10,
            },
            {
                "event": "PostToolUse",
                "matcher": "Bash",
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/error-to-codex.py"',
                "timeout": 10,
            },
            {
                "event": "PostToolUse",
                "matcher": "Bash",
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/post-test-analysis.py"',
                "timeout": 10,
            },
            {
                "event": "PostToolUse",
                "matcher": "Bash",
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/log-cli-tools.py"',
                "timeout": 5,
            },
            {
                "event": "PostToolUse",
                "matcher": "Edit|Write",
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/post-implementation-review.py"',
                "timeout": 10,
            },
            {
                "event": "TaskCompleted",
                "matcher": None,
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/log-cli-tools.py"',
                "timeout": 5,
            },
        ],
    },
    4: {
        "name": "Agent Teams",
        "description": "Parallel workflows with Agent Teams (requires Opus 4.6)",
        "files": [
            ".claude/skills/startproject/SKILL.md",
            ".claude/skills/startproject/references/task-patterns.md",
            ".claude/skills/team-implement/SKILL.md",
            ".claude/skills/team-review/SKILL.md",
            ".claude/skills/deploy/SKILL.md",
        ],
        "settings_env": {
            "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
            "CLAUDE_CODE_SUBAGENT_MODEL": "claude-opus-4-6",
        },
        "settings_hooks": [
            {
                "event": "TeammateIdle",
                "matcher": None,
                "command": (
                    'echo \'{"hookSpecificOutput": {"feedback": '
                    '"Check the shared task list for pending tasks. '
                    "If all tasks are complete, verify results and "
                    "report to the team lead.\"}}'"
                ),
                "timeout": 10,
            },
        ],
    },
    5: {
        "name": "Session Management",
        "description": "Checkpointing and project initialization",
        "files": [
            ".claude/skills/checkpointing/SKILL.md",
            ".claude/skills/checkpointing/checkpoint.py",
            ".claude/skills/init/SKILL.md",
        ],
        "dirs": [".claude/logs/", ".claude/checkpoints/"],
        "settings_hooks": [
            {
                "event": "PreCompact",
                "matcher": "auto",
                "command": (
                    'echo \'{"hookSpecificOutput": {"additionalContext": '
                    '"Context compaction triggered. Key context: '
                    "Check CLAUDE.md for project rules, "
                    ".claude/docs/DESIGN.md for design decisions, "
                    ".claude/rules/ for coding standards.\"}}'"
                ),
                "timeout": 10,
            },
        ],
    },
}

MIGRATED_PHASES_FILE = ".claude/.migrated-phases"


def generate_claude_md_header(project_name: str) -> str:
    """Generate CLAUDE.md header for new files."""
    return (
        f"# {project_name}\n"
        "\n"
        "<!-- Sections below added by migrate-skills.py -->\n"
        "\n"
        "---\n"
    )


def generate_claude_md_sections(phases: set[int]) -> str:
    """Generate CLAUDE.md sections for the given phases."""
    sections = []
    for phase_num in sorted(phases):
        if phase_num in CLAUDE_MD_SNIPPETS:
            sections.append(CLAUDE_MD_SNIPPETS[phase_num])
    return "\n".join(sections)


def run_fzf(
    input_lines: list[str], *, multi: bool = False, header: str = ""
) -> list[str]:
    """Run fzf with given input and return selected lines."""
    cmd = ["fzf", "--reverse", "--ansi"]
    if multi:
        cmd.append("--multi")
    if header:
        cmd.extend(["--header", header])

    try:
        result = subprocess.run(
            cmd,
            input="\n".join(input_lines),
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return []
    except FileNotFoundError:
        print("Error: fzf is not installed. Install it or use --phase/--target flags.")
        sys.exit(1)

    return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]


def select_phases_interactive() -> list[int]:
    """Select phases interactively using fzf."""
    lines = []
    for num, info in PHASES.items():
        file_count = len(info["files"])
        lines.append(
            f"Phase {num}: {info['name']} ({file_count} files) - {info['description']}"
        )

    selected = run_fzf(
        lines, multi=True, header="Select phases to migrate (TAB to multi-select)"
    )
    phases = []
    for line in selected:
        num = int(line.split(":")[0].replace("Phase ", ""))
        phases.append(num)
    return sorted(phases)


def _prompt_manual_path() -> Path:
    """Prompt user to enter a directory path manually."""
    raw = input("Enter target directory path: ").strip()
    if not raw:
        return Path()
    target = Path(raw).expanduser().resolve()
    if not target.is_dir():
        print(f"Error: Not a directory: {target}")
        return Path()
    return target


def select_target_interactive() -> Path:
    """Select target repository interactively using fzf."""
    home = Path.home()
    try:
        result = subprocess.run(
            [
                "find",
                str(home),
                "-maxdepth",
                "5",
                "-name",
                ".git",
                "-type",
                "d",
                "-not",
                "-path",
                "*/node_modules/*",
                "-not",
                "-path",
                "*/.cache/*",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        result = None

    # Also try to discover worktrees where .git is a file.
    try:
        result_git_file = subprocess.run(
            [
                "find",
                str(home),
                "-maxdepth",
                "5",
                "-name",
                ".git",
                "-type",
                "f",
                "-not",
                "-path",
                "*/node_modules/*",
                "-not",
                "-path",
                "*/.cache/*",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        result_git_file = None

    manual_entry = "[Enter path manually]"
    repos = [manual_entry]

    if result and result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            repo_path = line.strip().removesuffix("/.git")
            if repo_path and repo_path != str(SOURCE_ROOT):
                repos.append(repo_path)

    if result_git_file and result_git_file.stdout.strip():
        for line in result_git_file.stdout.strip().splitlines():
            repo_path = line.strip().removesuffix("/.git")
            if repo_path and repo_path != str(SOURCE_ROOT):
                repos.append(repo_path)

    repos_sorted = [repos[0], *sorted(repos[1:])]
    selected = run_fzf(
        repos_sorted, header="Select target directory (or enter path manually)"
    )
    if not selected:
        return Path()
    if selected[0] == manual_entry:
        return _prompt_manual_path()
    return Path(selected[0])


def get_migrated_phases(target: Path) -> set[int]:
    """Read previously migrated phases from target."""
    marker = target / MIGRATED_PHASES_FILE
    if not marker.exists():
        return set()
    try:
        data = json.loads(marker.read_text())
        if not isinstance(data, dict):
            return set()
        phases = data.get("phases", [])
        if not isinstance(phases, list):
            return set()
        return set(phases)
    except (json.JSONDecodeError, OSError, TypeError):
        return set()


def record_migrated_phases(target: Path, phases: list[int]) -> None:
    """Record migrated phases in target."""
    marker = target / MIGRATED_PHASES_FILE
    existing = get_migrated_phases(target)
    existing.update(phases)
    data = {
        "phases": sorted(existing),
        "last_migrated": datetime.now(UTC).isoformat(),
        "source": str(SOURCE_ROOT),
    }
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(data, indent=2) + "\n")


def apply_settings_merge(
    target: Path,
    hooks: list[dict],
    permissions: list[str],
    env: dict[str, str],
) -> dict[str, int]:
    """Merge hooks, permissions, and env into target's .claude/settings.json.

    Single read-modify-write to avoid multiple file I/O.
    Returns counts dict with hooks_added, hooks_skipped, perms_added, env_added.
    """
    settings_path = target / ".claude" / "settings.json"

    if settings_path.exists():
        settings = json.loads(settings_path.read_text())
    else:
        settings = {}

    counts = {"hooks_added": 0, "hooks_skipped": 0, "perms_added": 0, "env_added": 0}

    # --- Merge hooks ---
    if hooks:
        if "hooks" not in settings:
            settings["hooks"] = {}

        for entry in hooks:
            event = entry["event"]
            matcher = entry.get("matcher")
            command = entry["command"]
            timeout = entry.get("timeout", 10)

            if event not in settings["hooks"]:
                settings["hooks"][event] = []

            matcher_entry = None
            for existing in settings["hooks"][event]:
                if existing.get("matcher") == matcher:
                    matcher_entry = existing
                    break

            if matcher_entry is None:
                matcher_entry = {"hooks": []}
                if matcher is not None:
                    matcher_entry["matcher"] = matcher
                settings["hooks"][event].append(matcher_entry)

            already_exists = any(
                h.get("command") == command for h in matcher_entry.get("hooks", [])
            )

            if already_exists:
                counts["hooks_skipped"] += 1
            else:
                matcher_entry.setdefault("hooks", []).append(
                    {"type": "command", "command": command, "timeout": timeout}
                )
                counts["hooks_added"] += 1

    # --- Merge permissions ---
    if permissions:
        allow_list = settings.setdefault("permissions", {}).setdefault("allow", [])
        for perm in permissions:
            if perm not in allow_list:
                allow_list.append(perm)
                counts["perms_added"] += 1

    # --- Merge env ---
    if env:
        env_dict = settings.setdefault("env", {})
        for key, value in env.items():
            if key not in env_dict:
                env_dict[key] = value
                counts["env_added"] += 1

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")

    return counts


def collect_operations(phases: list[int], target: Path, *, force: bool = False) -> dict:
    """Collect all file operations for the selected phases.

    Returns a dict with:
        - copy: list of (src, dst) tuples for file copies
        - template: list of (dst, content) tuples for template generation
        - mkdir: list of Path objects for directory creation
        - skip: list of (dst, reason) tuples for skipped files
    """
    ops: dict = {
        "copy": [],
        "template": [],
        "mkdir": [],
        "skip": [],
        "settings_hooks": [],
        "settings_permissions": [],
        "settings_env": {},
        "claude_md": "",
        "claude_md_phases": [],
    }

    for phase_num in phases:
        phase = PHASES[phase_num]

        # Directories to create
        for dir_path in phase.get("dirs", []):
            ops["mkdir"].append(target / dir_path)

        # Files to copy
        for file_path in phase.get("files", []):
            src = SOURCE_ROOT / file_path
            dst = target / file_path

            if not src.exists():
                ops["skip"].append((str(file_path), "source not found"))
                continue

            if dst.exists() and not force:
                ops["skip"].append(
                    (str(file_path), "already exists (use --force to overwrite)")
                )
                continue

            ops["copy"].append((src, dst))

        # Templates to generate
        for file_path, content in phase.get("templates", {}).items():
            dst = target / file_path
            if dst.exists() and not force:
                ops["skip"].append(
                    (str(file_path), "already exists (use --force to overwrite)")
                )
                continue
            ops["template"].append((dst, content))

        # Settings hooks to merge
        for hook_entry in phase.get("settings_hooks", []):
            ops["settings_hooks"].append(hook_entry)

        # Settings permissions to merge
        for perm in phase.get("settings_permissions", []):
            if perm not in ops["settings_permissions"]:
                ops["settings_permissions"].append(perm)

        # Settings env to merge
        ops["settings_env"].update(phase.get("settings_env", {}))

    # Generate CLAUDE.md sections for current phases
    ops["claude_md"] = generate_claude_md_sections(set(phases))
    ops["claude_md_phases"] = sorted(set(phases))

    return ops


def print_preview(ops: dict, phases: list[int], target: Path) -> None:
    """Print a preview of operations to be performed."""
    print(f"\n{'=' * 60}")
    print("Migration Preview")
    print(f"{'=' * 60}")
    phase_labels = ", ".join(f"{p} ({PHASES[p]['name']})" for p in phases)
    print(f"  Phases: {phase_labels}")
    print(f"  Target: {target}")
    print(f"{'=' * 60}")

    if ops["mkdir"]:
        print(f"\n  Directories to create ({len(ops['mkdir'])}):")
        for d in ops["mkdir"]:
            exists = " (exists)" if d.exists() else ""
            print(f"    + {d.relative_to(target)}/{exists}")

    if ops["copy"]:
        print(f"\n  Files to copy ({len(ops['copy'])}):")
        for _, dst in ops["copy"]:
            print(f"    + {dst.relative_to(target)}")

    if ops["template"]:
        print(f"\n  Templates to generate ({len(ops['template'])}):")
        for dst, _ in ops["template"]:
            print(f"    + {dst.relative_to(target)}")

    if ops["settings_hooks"]:
        print(f"\n  Settings hooks to register ({len(ops['settings_hooks'])}):")
        for entry in ops["settings_hooks"]:
            matcher_str = f" [{entry['matcher']}]" if entry.get("matcher") else ""
            print(f"    + {entry['event']}{matcher_str}")

    if ops["settings_permissions"]:
        print(f"\n  Permissions to add ({len(ops['settings_permissions'])}):")
        for perm in ops["settings_permissions"]:
            print(f"    + {perm}")

    if ops["settings_env"]:
        print(f"\n  Environment variables to set ({len(ops['settings_env'])}):")
        for key, value in ops["settings_env"].items():
            print(f"    + {key}={value}")

    if ops.get("claude_md"):
        claude_md_path = target / "CLAUDE.md"
        action = "append" if claude_md_path.exists() else "create"
        print(f"\n  CLAUDE.md: {action}")

    if ops["skip"]:
        print(f"\n  Skipped ({len(ops['skip'])}):")
        for path, reason in ops["skip"]:
            print(f"    - {path}: {reason}")

    total = len(ops["copy"]) + len(ops["template"])
    hooks_count = len(ops["settings_hooks"])
    print(
        f"\n  Total: {total} file(s) to write, {len(ops['mkdir'])} dir(s) to create",
        end="",
    )
    if hooks_count:
        print(f", {hooks_count} hook(s) to register")
    else:
        print()
    print()


def execute_operations(ops: dict, target: Path) -> dict:
    """Execute the collected operations. Returns summary counts."""
    counts = {
        "copied": 0,
        "templated": 0,
        "dirs_created": 0,
        "hooks_added": 0,
        "hooks_skipped": 0,
        "claude_md_written": False,
        "errors": 0,
    }

    for dir_path in ops["mkdir"]:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            counts["dirs_created"] += 1
        except OSError as e:
            print(f"  Error creating {dir_path}: {e}")
            counts["errors"] += 1

    for src, dst in ops["copy"]:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            counts["copied"] += 1
        except OSError as e:
            print(f"  Error copying {src.name}: {e}")
            counts["errors"] += 1

    for dst, content in ops["template"]:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content)
            counts["templated"] += 1
        except OSError as e:
            print(f"  Error writing {dst.name}: {e}")
            counts["errors"] += 1

    has_settings = (
        ops["settings_hooks"] or ops["settings_permissions"] or ops["settings_env"]
    )
    if has_settings:
        try:
            merge_counts = apply_settings_merge(
                target,
                hooks=ops["settings_hooks"],
                permissions=ops["settings_permissions"],
                env=ops["settings_env"],
            )
            counts.update(merge_counts)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  Error merging settings: {e}")
            counts["errors"] += 1

    # Write/append CLAUDE.md
    if ops.get("claude_md"):
        try:
            claude_md_path = target / "CLAUDE.md"
            if claude_md_path.exists():
                existing_text = claude_md_path.read_text()
                snippets_to_add: list[str] = []
                for phase_num in ops.get("claude_md_phases", []):
                    snippet = CLAUDE_MD_SNIPPETS.get(phase_num)
                    if not snippet:
                        continue
                    if snippet.strip() in existing_text:
                        continue
                    snippets_to_add.append(snippet)

                if snippets_to_add:
                    with claude_md_path.open("a") as f:
                        f.write("\n" + "\n".join(snippets_to_add))
            else:
                header = generate_claude_md_header(target.name)
                claude_md_path.write_text(header + "\n" + ops["claude_md"])
            counts["claude_md_written"] = True
        except OSError as e:
            print(f"  Error writing CLAUDE.md: {e}")
            counts["errors"] += 1

    return counts


def print_summary(counts: dict, phases: list[int], target: Path) -> None:
    """Print execution summary."""
    print(f"\n{'=' * 60}")
    print("Migration Complete")
    print(f"{'=' * 60}")
    print(f"  Phases migrated: {', '.join(str(p) for p in phases)}")
    print(f"  Files copied:    {counts['copied']}")
    print(f"  Templates:       {counts['templated']}")
    print(f"  Dirs created:    {counts['dirs_created']}")
    if counts.get("hooks_added"):
        print(f"  Hooks added:     {counts['hooks_added']}")
    if counts.get("hooks_skipped"):
        print(f"  Hooks skipped:   {counts['hooks_skipped']} (already registered)")
    if counts.get("perms_added"):
        print(f"  Perms added:     {counts['perms_added']}")
    if counts.get("env_added"):
        print(f"  Env vars added:  {counts['env_added']}")
    if counts.get("claude_md_written"):
        print("  CLAUDE.md:       written")
    if counts["errors"]:
        print(f"  Errors:          {counts['errors']}")
    print(f"  Target:          {target}")
    print()

    already = get_migrated_phases(target)
    if already:
        print(f"  All migrated phases: {', '.join(str(p) for p in sorted(already))}")
        remaining = set(PHASES.keys()) - already
        if remaining:
            print(
                f"  Remaining phases:    {', '.join(str(p) for p in sorted(remaining))}"
            )
        else:
            print("  All phases migrated!")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate skills and rules to target repositories.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--phase",
        type=str,
        default=None,
        help="Comma-separated phase numbers (e.g. '0,1,2'). Skips fzf selection.",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Target repository path. Skips fzf selection.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview operations without executing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files in target.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print("Claude Code Orchestra - Skill Migration Tool")
    print(f"Source: {SOURCE_ROOT}\n")

    # Phase selection
    if args.phase is not None:
        try:
            phases = sorted({int(p.strip()) for p in args.phase.split(",") if p.strip()})
        except ValueError:
            print("Error: --phase must be comma-separated integers (e.g. '0,1,2')")
            return 1
        invalid = [p for p in phases if p not in PHASES]
        if invalid:
            print(f"Error: Invalid phase(s): {invalid}. Valid: 0-{max(PHASES.keys())}")
            return 1
    else:
        phases = select_phases_interactive()
        if not phases:
            print("No phases selected. Exiting.")
            return 0

    # Target selection
    if args.target is not None:
        target = Path(args.target).resolve()
        if not target.is_dir():
            print(f"Error: Target directory does not exist: {target}")
            return 1
    else:
        target = select_target_interactive()
        if not target or not target.is_dir():
            print("No target selected. Exiting.")
            return 0

    if target == SOURCE_ROOT:
        print("Error: Cannot migrate to the source repository itself.")
        return 1

    # Check previously migrated phases
    migrated = get_migrated_phases(target)
    already_done = set(phases) & migrated
    if already_done and not args.force:
        print(
            f"Warning: Phase(s) {sorted(already_done)} already migrated to this target."
        )
        print("  Use --force to re-migrate, or select different phases.")
        phases = [p for p in phases if p not in already_done]
        if not phases:
            print("No new phases to migrate. Exiting.")
            return 0
        print(f"  Continuing with phase(s): {phases}\n")

    # Collect and preview operations
    ops = collect_operations(phases, target, force=args.force)
    print_preview(ops, phases, target)

    total_writes = len(ops["copy"]) + len(ops["template"])
    has_settings = (
        ops["settings_hooks"] or ops["settings_permissions"] or ops["settings_env"]
    )
    if (
        total_writes == 0
        and not ops["mkdir"]
        and not has_settings
        and not ops.get("claude_md")
    ):
        print("Nothing to do. All files already exist or sources are missing.")
        return 0

    if args.dry_run:
        print("[Dry run] No files were modified.")
        return 0

    # Confirmation
    answer = input("Proceed with migration? [y/N] ").strip().lower()
    if answer != "y":
        print("Cancelled.")
        return 0

    # Execute
    print("\nMigrating...")
    counts = execute_operations(ops, target)
    if counts["errors"] == 0:
        record_migrated_phases(target, phases)
    else:
        print("  Warning: Migration had errors; not recording migrated phases marker.")
    print_summary(counts, phases, target)

    return 1 if counts["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
