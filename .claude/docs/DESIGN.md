# Project Design Document

> This document tracks design decisions made during conversations.
> Updated automatically by the `design-tracker` skill.

## Overview

Claude Code Orchestra is a multi-agent collaboration framework that orchestrates Claude Code (1M context), OpenCode CLI (deep reasoning), and Gemini CLI (external research + multimodal) to accelerate development. With Opus 4.6, the framework leverages Agent Teams for parallel work.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude Code Lead (Opus 4.6 — 1M context)                       │
│  Role: Orchestration, codebase analysis, user interaction        │
│                                                                   │
│  ┌──────────────────────┐  ┌──────────────────────┐             │
│  │ Agent Teams           │  │ Subagents             │             │
│  │ (parallel + comms)    │  │ (isolated + results)  │             │
│  │                       │  │                       │             │
│  │ Researcher ←→ Archit. │  │ OpenCode consultation │             │
│  │ Implementer A/B/C     │  │ Gemini research       │             │
│  │ Security/Quality Rev. │  │ Error analysis        │             │
│  └──────────────────────┘  └──────────────────────┘             │
│                                                                   │
│  External CLIs:                                                   │
│  ├── OpenCode CLI (github-copilot/gpt-5.4) — deep reasoning, design │
│  └── Gemini CLI (gemini-3-pro) — web search, multimodal          │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Patterns & Approaches

| Pattern | Purpose | Notes |
|---------|---------|-------|
| Agent Teams | Parallel work with inter-agent communication | /startproject, /team-implement, /team-review |
| Subagents | Isolated tasks returning results | OpenCode/Gemini consultation when teams not needed |
| Skill Pipeline | `/startproject` → `/team-implement` → `/team-review` | Separation of concerns across skills |
| Decision Journal | Consistent cross-phase decision logging | Local append-only canonical log + Linear mirror sync |

### Execution Sizing (Adaptive)

| Size | Typical Scope | Planning Mode | Implementation Mode | Review Mode |
|------|---------------|---------------|---------------------|-------------|
| XS | 1 file, low-risk, no design decision | Skip teams and subagents | Claude direct | Optional or spot-check |
| S | 1-3 files, clear requirement, known pattern | Skip Agent Teams | Claude direct | Single reviewer |
| M | 4-10 files or moderate design/risk | Targeted subagent consultation | Claude direct or 1-2 implementers | 2 reviewers |
| L | 10+ files, cross-cutting, new dependency, migration | Full Agent Teams (Researcher + Architect) | Full implementation team | Full 4-reviewer team |

Classification is hybrid: file count + complexity + risk/novelty. Runtime escalation is allowed when scope grows.

### Libraries & Roles

| Library | Role | Version | Notes |
|---------|------|---------|-------|
| OpenCode CLI | Deep reasoning partner | github-copilot/gpt-5.4 | Design, debug, trade-offs |
| Gemini CLI | External information + multimodal | gemini-3-pro | Web search, PDF/video/audio |

### Key Decisions

| Decision | Rationale | Alternatives Considered | Date |
|----------|-----------|------------------------|------|
| Claude handles codebase analysis directly | Opus 4.6 has 1M context, no need to delegate to Gemini | Keep Gemini for codebase analysis | 2026-02-08 |
| Gemini role narrowed to external info + multimodal | Claude's 1M context makes Gemini's codebase analysis redundant; Gemini's unique value is Google Search and multimodal | Keep broad Gemini role | 2026-02-08 |
| /startproject split into 3 skills | Separation of Plan/Implement/Review gives user control gates | Single monolithic skill | 2026-02-08 |
| Agent Teams for Research ↔ Design | Bidirectional communication enables iterative refinement | Sequential subagents (old approach) | 2026-02-08 |
| Agent Teams for parallel implementation | Module-based ownership avoids file conflicts | Single-agent sequential implementation | 2026-02-08 |
| Subagent threshold relaxed to ~50 lines | 1M context can absorb more direct output | Keep 10-line threshold | 2026-02-08 |
| Use pre/post checkpoints per phase with local-first dual-write | Keeps logs consistent across `/startproject`, `/team-implement`, `/team-review`, `/deploy` while minimizing external write overhead | Write Linear only (no local canonical log), per-phase separate log files | 2026-02-16 |
| Hybrid MADR + Y-statements template approach | MADR forces "considered options" for local docs; Y-statements are concise for Linear comments | Pure MADR everywhere, pure Y-statements everywhere | 2026-02-16 |
| Markdown format over JSONL for decision log | Human-readable, git-friendly diffs, no tooling needed; JSONL mirror can be added later if machine-queryable logs needed | JSONL (OpenCode recommendation) | 2026-02-16 |
| 5-6 Linear comments per feature lifecycle | Reduces API noise while maintaining visibility; each comment is a coherent phase summary | Per-event comments (noisy), no comments (invisible) | 2026-02-16 |
| Adaptive execution tiers (XS/S/M/L) added | Reduce over-orchestration on small tasks while preserving depth for large work | Single heavyweight workflow for all tasks | 2026-02-16 |
| Task sizing should use hybrid signals | File count alone misses complexity and risk | File-count-only classification | 2026-02-16 |
| Runtime promotion (S→M→L) should be explicit | Prevent under-scoped execution when tasks expand during implementation | Static upfront classification only | 2026-02-16 |

## TODO

- [ ] Update gemini-system and opencode-system skills to match new delegation rules
- [ ] Test Agent Teams workflow end-to-end with a real project
- [ ] Evaluate if gemini-explore agent should be removed or repurposed
- [ ] Update hooks for Agent Teams quality gates
- [ ] Define decision log schema (`decision_id`, `workflow_run_id`, `phase`, `checkpoint`, `summary`, `rationale`, `sync_status`)
- [ ] Implement Linear sync worker (batch on post-phase, retry failed entries)
- [x] Implement task sizing heuristic (file count + complexity + risk score) → `.claude/rules/adaptive-execution.md`
- [x] Define auto-escalation triggers and handoff checkpoints between XS/S/M/L → `.claude/rules/adaptive-execution.md`
- [ ] Add telemetry: initial size vs final size, escalation rate, cycle time, defect rate

## Decision Logging Architecture

### Overview

All 4 workflow skills (`/startproject`, `/team-implement`, `/team-review`, `/deploy`) follow a
consistent dual-logging pattern: local-first writes to a canonical decision log, with batched
Linear sync at phase boundaries.

### Core Pattern: PRE / DECISION / POST

Every phase emits exactly 3 event types:

| Event | When | Purpose |
|-------|------|---------|
| **PRE** | Phase start | Record intent, inputs, preconditions |
| **DECISION** | During phase (0..N) | Record each significant decision with rationale |
| **POST** | Phase end | Record outcomes, artifacts produced, handoff to next phase |

### Dual-Write Strategy: Local-First + Batched Linear Sync

```
1. LOCAL WRITE (immediate, every event)
   → Append to `.claude/docs/decisions/log-{feature}.md`
   → Also update phase-specific summary files as needed

2. LINEAR SYNC (batched at POST checkpoint)
   → Collect all PRE + DECISION + POST entries for the phase
   → Format as single Japanese comment on Linear task
   → Route via Gemini subagent (plan) → Claude MCP (execute)
   → On failure: mark sync_status=pending, retry next phase
```

**Why local-first**: Immediate, no external dependency, survives MCP failures.
**Why batched Linear**: Reduces API calls, produces coherent phase-level comments
instead of noisy per-event comments.

### Template Approach: Hybrid MADR + Y-Statements

Based on Researcher findings (`.claude/docs/research/decision-logging-practices.md`):

- **Local docs (log.md)**: MADR-inspired structured entries with PRE/DECISION/POST
- **Linear comments**: Y-statement style concise summaries in Japanese
  (format: "Xの文脈で、Yに直面し、Wを達成するためにZを決定、Vを受容")
- **DESIGN.md**: Full MADR for major architectural decisions

### Phase Boundary Completeness Checklists

Each phase boundary includes verification:

```
PRE checkpoint:
- [ ] Intent and inputs recorded in log.md
- [ ] Preconditions verified

DECISION checkpoint (during phase):
- [ ] Each significant decision has rationale recorded
- [ ] Alternatives considered are noted

POST checkpoint:
- [ ] Outcomes and artifacts listed in log.md
- [ ] Local summary file saved (if applicable)
- [ ] Linear comment posted with phase summary
- [ ] Handoff instructions for next phase
```

### Linear Comment Volume Target

3-4 comments per feature lifecycle:
- startproject: 1 (Phase 3 POST — consolidated)
- team-implement: 1 (Step 0 design record; Step 5 uses existing Linear template)
- team-review: 0 (local doc only — review results are not posted to Linear)
- deploy: 1 (Step 4 deploy info — Japanese template)

### File Organization

```
.claude/docs/decisions/
  ├── log-{feature}.md              # Canonical append-only decision log (all phases)
  ├── brief-{feature}.md            # Phase 1 output (startproject)
  └── implementation-{feature}.md   # Phase 4 output (team-implement Step 5)
```

**Flat directory** with `log-{feature}.md` naming convention. Single canonical log
per feature, with entries chronologically ordered across all phases.
This avoids nested directories and makes cross-phase auditing easy.

### Log Entry Format (Markdown)

```markdown
### [{phase}] {event_type} — {timestamp}

- **Actor**: {agent or user}
- **Summary**: {one-line description}
- **Rationale**: {why this decision was made}
- **Status**: {proposed | accepted | rejected | deferred}
- **Artifacts**: {list of files created/modified, if any}

{optional details paragraph}
```

### Linear Comment Template (Japanese)

Each phase's POST checkpoint generates a single Linear comment:

```markdown
## {phase_label}: {feature}

### 概要
{phase summary in 2-3 sentences}

### 決定事項
- {decision 1}: {rationale}
- {decision 2}: {rationale}

### 成果物
- {artifact 1}
- {artifact 2}

### 次のステップ
- {handoff instructions}
```

---

### Gap Solutions (9 Gaps)

#### Gap 1: startproject Phase 1 — Project Brief not saved

**Location**: `startproject/SKILL.md` Phase 1, Step 4 (Create Project Brief)

**Current**: Brief is created in-memory and "passed to Phase 2 teammates as shared context."

**Fix**: Add save step after creating the brief.

```markdown
#### Step 4b: Save Project Brief

Save the project brief to the local decision log:

1. Create `.claude/docs/decisions/brief-{feature}.md` with the full brief content
2. Append a PRE entry to `.claude/docs/decisions/log-{feature}.md`:

### [startproject] PRE — {date}
- **Actor**: Claude Lead
- **Summary**: Project brief created for {feature}
- **Artifacts**: `.claude/docs/decisions/brief-{feature}.md`
```

**Linear**: No separate sync needed — included in Phase 3 POST sync.

---

#### Gap 2: startproject Phase 1 — Requirements gathering decisions not recorded

**Location**: `startproject/SKILL.md` Phase 1, Step 3 (Requirements Gathering)

**Current**: Requirements are gathered via conversation but not persisted.

**Fix**: Add recording step after requirements are clarified.

```markdown
#### Step 3b: Record Requirements Decisions

After requirements gathering, append DECISION entries to the log for each
significant requirement decision:

Append to `.claude/docs/decisions/log-{feature}.md`:

### [startproject] DECISION — {date}
- **Actor**: User + Claude Lead
- **Summary**: {requirement decision, e.g., "Scope excludes admin panel"}
- **Rationale**: {user's reasoning}
- **Status**: accepted
```

**Linear**: Included in Phase 3 POST sync as part of "決定事項".

---

#### Gap 3: team-implement Step 0 — design-tracker updates DESIGN.md but NOT Linear

**Location**: `team-implement/SKILL.md` Step 0 (Record Design Decisions)

**Current**: `/design-tracker` updates DESIGN.md only.

**Fix**: Add Linear sync after design-tracker completes.

```markdown
#### Step 0b: Sync Design Decisions to Linear

After `/design-tracker` completes, post design snapshot to Linear:

Linear comment (Japanese):
## 設計記録: {feature}

### アーキテクチャ
- {architecture decisions from DESIGN.md}

### 技術選定
- {library choices and rationale}

### 主要な設計判断
- {key decisions with dates}

Routing: Gemini subagent plans → Claude MCP executes
```

Also append a PRE entry to `.claude/docs/decisions/log-{feature}.md`:

```markdown
### [team-implement] PRE — {date}
- **Actor**: Claude Lead
- **Summary**: Implementation phase started, design decisions recorded
- **Artifacts**: `.claude/docs/DESIGN.md` (updated by design-tracker)
```

---

#### Gap 4: team-implement Step 1 — Branch creation info not recorded

**Location**: `team-implement/SKILL.md` Step 1 (Create Feature Branch)

**Current**: Branch is created but not logged anywhere.

**Fix**: Add recording step after branch creation.

```markdown
#### Step 1b: Record Branch Info

Append to `.claude/docs/decisions/log-{feature}.md`:

### [team-implement] DECISION — {date}
- **Actor**: Claude Lead (via Gemini subagent)
- **Summary**: Feature branch `feature/{feature-name}` created from `{base-branch}`
- **Rationale**: Standard feature branch workflow
- **Status**: accepted
- **Artifacts**: Branch `feature/{feature-name}`
```

**Linear**: Included in Step 5 POST sync.

---

#### Gap 5: team-implement Steps 3-4 — Implementation decisions during monitoring not recorded

**Location**: `team-implement/SKILL.md` Steps 3-4 (Spawn & Monitor)

**Current**: Lead monitors but doesn't record intervention decisions.

**Fix**: Add decision logging to intervention triggers.

```markdown
#### Step 4b: Record Implementation Decisions

When Lead makes intervention decisions during monitoring, append DECISION entries:

### [team-implement] DECISION — {date}
- **Actor**: Claude Lead
- **Summary**: {intervention description, e.g., "Reassigned file ownership for models.py"}
- **Rationale**: {why, e.g., "File conflict detected between Implementer-A and Implementer-B"}
- **Status**: accepted

Triggers for recording:
- File ownership reassignment
- Teammate re-instruction
- Technical problem resolution (especially OpenCode consultations)
- Scope changes during implementation
```

**Linear**: Included in Step 5 POST sync as part of "決定事項".

---

#### Gap 6: team-implement Step 5 — Linear posted but NO local doc

**Location**: `team-implement/SKILL.md` Step 5 (Integration & Verification)

**Current**: Integration report and commit info posted to Linear, but no local file saved.

**Fix**: Save implementation summary locally and append POST entry.

```markdown
#### Step 5b: Save Implementation Summary Locally

1. Save implementation summary to `.claude/docs/decisions/implementation-{feature}.md`:

## Implementation Summary: {feature}

### Completed Tasks
- [x] {task 1}
- [x] {task 2}

### Quality Checks
- ruff: pass/fail
- ty: pass/fail
- pytest: {N} tests, {coverage}%

### Commits
- {hash}: {message}

### Key Decisions During Implementation
- {decision 1}: {rationale}

2. Append POST entry to `.claude/docs/decisions/log-{feature}.md`:

### [team-implement] POST — {date}
- **Actor**: Claude Lead
- **Summary**: Implementation complete, {N} tasks done, all quality checks passed
- **Artifacts**: `.claude/docs/decisions/implementation-{feature}.md`
```

---

#### Gap 7: team-review Steps 3-4 — Review results not recorded locally

**Location**: `team-review/SKILL.md` Steps 3-4 (Synthesize & Report)

**Current**: Review results synthesized and shown to user, but not persisted to local docs.

**Fix**: Add local doc recording after presenting to user (Step 4b). No Linear posting.

```markdown
#### Step 4b: Record Review Results Locally

After presenting review results to the user, append POST entry to `.claude/docs/decisions/log-{feature}.md`:

### [team-review] POST — {date}
- **Actor**: Claude Lead
- **Summary**: Review complete — {critical} critical, {high} high findings
- **Artifacts**: Review reports in `.claude/docs/research/review-*-{feature}.md`

### Review Summary
- Security: {security_count} findings (Critical: {n}, High: {n})
- Quality: {quality_count} findings
- Test Coverage: {coverage}%
- Simplify candidates: {simplify_count}
```

**Linear**: Not posted (local doc only).

---

#### Gap 8: team-review Step 5 — Simplify results not recorded

**Location**: `team-review/SKILL.md` Step 5 (Simplify)

**Current**: Simplify refactoring is executed and shown to user, but not logged.

**Fix**: Add local doc recording after simplify completion. No Linear posting.

```markdown
#### Step 5b: Record Simplify Results Locally

Append to `.claude/docs/decisions/log-{feature}.md`:

### [team-review] DECISION — {date}
- **Actor**: Claude Lead
- **Summary**: Simplify refactoring applied to {N} files
- **Rationale**: User approved simplifications #{selected numbers}
- **Status**: accepted
- **Artifacts**: Modified files listed below

### Simplify Details
| # | File | Change | Test |
|---|------|--------|------|
| 1 | `{file}` | {change} | pass |
```

**Linear**: Not posted (local doc only).

---

#### Gap 9: deploy Step 4 — Linear posted but NO local doc + Linear not in Japanese

**Location**: `deploy/SKILL.md` Step 4 (Post Deploy Info to Linear)

**Current**: Deploy info posted to Linear in mixed language, but no local record.

**Fix**: Add local doc recording AND convert existing Linear template to full Japanese.

```markdown
#### Step 4b: Save Deploy Record Locally + Japanese Linear Template

1. Append POST entry to `.claude/docs/decisions/log-{feature}.md`:

### [deploy] POST — {date}
- **Actor**: Claude Lead (via Gemini subagent)
- **Summary**: Feature branch pushed to origin, returned to {original-branch}
- **Artifacts**: Branch `feature/{feature-name}` on origin

### Deploy Details
- Branch: `feature/{feature-name}` → origin
- Commits: {N} commits
- Review status: {critical/high findings resolved}
- Linear: comment posted

2. Update Linear comment template to full Japanese:

## デプロイ完了: {feature}

### ブランチ
- [`feature/{feature-name}`]({branch URL}) → origin に push 済み

### コミット履歴
- [{commit hash}]({commit URL}): {commit message}

### レビュー結果サマリー
- セキュリティ: {summary}
- コード品質: {summary}
- テストカバレッジ: {summary}

### 次のステップ
- PR 作成 / マージ待ち
```

---

### Design Rationale Summary

| Design Choice | Rationale |
|---------------|-----------|
| Local-first writes | Immediate, reliable, no external dependency |
| Batched Linear sync at POST | Reduces API noise, produces coherent phase comments |
| Flat `log-{feature}.md` naming | Avoids nested directories, enables cross-phase audit trail |
| Markdown format (not JSONL) | Human-readable in-repo, easy to review in PRs |
| Japanese Linear comments | Matches team language protocol for external tools |
| PRE/DECISION/POST pattern | Consistent across all 4 phases, minimal cognitive overhead |

> **Note on JSONL vs Markdown**: OpenCode recommended JSONL for machine-readability.
> We chose Markdown because: (1) these logs are primarily human-consumed, (2) they
> live in a git repo where Markdown diffs are natural, (3) no tooling exists yet to
> query JSONL logs. If machine-queryable logs become needed, a JSONL mirror can be
> added later.

## Open Questions

- [ ] Exact scoring threshold for XS vs S when risk is low but touching core files
- [ ] Should M tasks default to Claude direct, or 1 implementer by default?
- [ ] How to handle Compaction in long Agent Teams sessions?

## Changelog

| Date | Changes |
|------|---------|
| 2026-02-16 | Full Decision Logging Architecture: 9-gap solutions, PRE/DECISION/POST pattern, local-first dual-write, per-feature decision directories, Linear sync templates (Japanese) |
| 2026-02-16 | Added adaptive execution sizing model (XS/S/M/L), hybrid classification principle, and runtime escalation policy |
| 2026-02-08 | Major redesign for Opus 4.6: 1M context, Agent Teams, skill pipeline |
| | Initial |
