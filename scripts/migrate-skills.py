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
from datetime import datetime, timezone
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

PHASES: dict[int, dict] = {
    0: {
        "name": "Foundation Rules",
        "description": "Base rules referenced by all skills",
        "files": [
            ".claude/rules/language.md",
            ".claude/rules/coding-principles.md",
            ".claude/rules/testing.md",
            ".claude/rules/security.md",
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
            ".claude/skills/codex-system/SKILL.md",
            ".claude/skills/codex-system/references/agent-prompts.md",
            ".claude/skills/codex-system/references/code-review-task.md",
            ".claude/skills/codex-system/references/delegation-patterns.md",
            ".claude/skills/codex-system/references/refactoring-task.md",
            ".claude/skills/codex-system/references/troubleshooting.md",
            ".claude/skills/gemini-system/SKILL.md",
            ".claude/skills/gemini-system/references/lib-research-task.md",
            ".claude/skills/gemini-system/references/use-cases.md",
        ],
        "dirs": [".claude/docs/research/"],
    },
    4: {
        "name": "Agent Teams",
        "description": "Parallel workflows with Agent Teams (requires Opus 4.6)",
        "files": [
            ".claude/skills/startproject/SKILL.md",
            ".claude/skills/startproject/references/task-patterns.md",
            ".claude/skills/team-implement/SKILL.md",
            ".claude/skills/team-review/SKILL.md",
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
    },
}

MIGRATED_PHASES_FILE = ".claude/.migrated-phases"


def run_fzf(input_lines: list[str], *, multi: bool = False, header: str = "") -> list[str]:
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
        lines.append(f"Phase {num}: {info['name']} ({file_count} files) - {info['description']}")

    selected = run_fzf(lines, multi=True, header="Select phases to migrate (TAB to multi-select)")
    phases = []
    for line in selected:
        num = int(line.split(":")[0].replace("Phase ", ""))
        phases.append(num)
    return sorted(phases)


def select_target_interactive() -> Path:
    """Select target repository interactively using fzf."""
    home = Path.home()
    try:
        result = subprocess.run(
            ["find", str(home), "-name", ".git", "-type", "d",
             "-not", "-path", "*/node_modules/*",
             "-not", "-path", "*/.cache/*",
             "-maxdepth", "5"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("Error: Could not search for git repositories.")
        sys.exit(1)

    repos = []
    for line in result.stdout.strip().splitlines():
        repo_path = line.strip().removesuffix("/.git")
        if repo_path and repo_path != str(SOURCE_ROOT):
            repos.append(repo_path)

    if not repos:
        print("Error: No git repositories found under home directory.")
        sys.exit(1)

    repos.sort()
    selected = run_fzf(repos, header="Select target repository")
    if not selected:
        return Path()
    return Path(selected[0])


def get_migrated_phases(target: Path) -> set[int]:
    """Read previously migrated phases from target."""
    marker = target / MIGRATED_PHASES_FILE
    if not marker.exists():
        return set()
    try:
        data = json.loads(marker.read_text())
        return set(data.get("phases", []))
    except (json.JSONDecodeError, KeyError):
        return set()


def record_migrated_phases(target: Path, phases: list[int]) -> None:
    """Record migrated phases in target."""
    marker = target / MIGRATED_PHASES_FILE
    existing = get_migrated_phases(target)
    existing.update(phases)
    data = {
        "phases": sorted(existing),
        "last_migrated": datetime.now(timezone.utc).isoformat(),
        "source": str(SOURCE_ROOT),
    }
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(data, indent=2) + "\n")


def collect_operations(phases: list[int], target: Path, *, force: bool = False) -> dict:
    """Collect all file operations for the selected phases.

    Returns a dict with:
        - copy: list of (src, dst) tuples for file copies
        - template: list of (dst, content) tuples for template generation
        - mkdir: list of Path objects for directory creation
        - skip: list of (dst, reason) tuples for skipped files
    """
    ops: dict = {"copy": [], "template": [], "mkdir": [], "skip": []}

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
                ops["skip"].append((str(file_path), "already exists (use --force to overwrite)"))
                continue

            ops["copy"].append((src, dst))

        # Templates to generate
        for file_path, content in phase.get("templates", {}).items():
            dst = target / file_path
            if dst.exists() and not force:
                ops["skip"].append((str(file_path), "already exists (use --force to overwrite)"))
                continue
            ops["template"].append((dst, content))

    return ops


def print_preview(ops: dict, phases: list[int], target: Path) -> None:
    """Print a preview of operations to be performed."""
    print(f"\n{'=' * 60}")
    print(f"Migration Preview")
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

    if ops["skip"]:
        print(f"\n  Skipped ({len(ops['skip'])}):")
        for path, reason in ops["skip"]:
            print(f"    - {path}: {reason}")

    total = len(ops["copy"]) + len(ops["template"])
    print(f"\n  Total: {total} file(s) to write, {len(ops['mkdir'])} dir(s) to create")
    print()


def execute_operations(ops: dict) -> dict:
    """Execute the collected operations. Returns summary counts."""
    counts = {"copied": 0, "templated": 0, "dirs_created": 0, "errors": 0}

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

    return counts


def print_summary(counts: dict, phases: list[int], target: Path) -> None:
    """Print execution summary."""
    print(f"\n{'=' * 60}")
    print(f"Migration Complete")
    print(f"{'=' * 60}")
    print(f"  Phases migrated: {', '.join(str(p) for p in phases)}")
    print(f"  Files copied:    {counts['copied']}")
    print(f"  Templates:       {counts['templated']}")
    print(f"  Dirs created:    {counts['dirs_created']}")
    if counts["errors"]:
        print(f"  Errors:          {counts['errors']}")
    print(f"  Target:          {target}")
    print()

    already = get_migrated_phases(target)
    if already:
        print(f"  All migrated phases: {', '.join(str(p) for p in sorted(already))}")
        remaining = set(PHASES.keys()) - already
        if remaining:
            print(f"  Remaining phases:    {', '.join(str(p) for p in sorted(remaining))}")
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

    print(f"Claude Code Orchestra - Skill Migration Tool")
    print(f"Source: {SOURCE_ROOT}\n")

    # Phase selection
    if args.phase is not None:
        try:
            phases = sorted(int(p.strip()) for p in args.phase.split(","))
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
        print(f"Warning: Phase(s) {sorted(already_done)} already migrated to this target.")
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
    if total_writes == 0 and not ops["mkdir"]:
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
    counts = execute_operations(ops)
    record_migrated_phases(target, phases)
    print_summary(counts, phases, target)

    return 1 if counts["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
