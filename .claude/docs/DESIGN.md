# Project Design Document

> This document tracks design decisions made during conversations.
> Updated automatically by the `design-tracker` skill.

## Overview

Claude Code Orchestra is a multi-agent collaboration framework that orchestrates Claude Code (1M context), Codex CLI (deep reasoning), and Gemini CLI (external research + multimodal) to accelerate development. With Opus 4.6, the framework leverages Agent Teams for parallel work.

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
│  │ Researcher ←→ Archit. │  │ Codex consultation    │             │
│  │ Implementer A/B/C     │  │ Gemini research       │             │
│  │ Security/Quality Rev. │  │ Error analysis        │             │
│  └──────────────────────┘  └──────────────────────┘             │
│                                                                   │
│  External CLIs:                                                   │
│  ├── Codex CLI (gpt-5.3-codex) — deep reasoning, design          │
│  └── Gemini CLI (gemini-3-pro) — web search, multimodal          │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Patterns & Approaches

| Pattern | Purpose | Notes |
|---------|---------|-------|
| Agent Teams | Parallel work with inter-agent communication | /startproject, /team-implement, /team-review |
| Subagents | Isolated tasks returning results | Codex/Gemini consultation when teams not needed |
| Skill Pipeline | `/startproject` → `/team-implement` → `/team-review` | Separation of concerns across skills |

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
| Codex CLI | Deep reasoning partner | gpt-5.3-codex | Design, debug, trade-offs |
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
| Adaptive execution tiers (XS/S/M/L) added | Reduce over-orchestration on small tasks while preserving depth for large work | Single heavyweight workflow for all tasks | 2026-02-16 |
| Task sizing should use hybrid signals | File count alone misses complexity and risk | File-count-only classification | 2026-02-16 |
| Runtime promotion (S→M→L) should be explicit | Prevent under-scoped execution when tasks expand during implementation | Static upfront classification only | 2026-02-16 |

## TODO

- [ ] Update gemini-system and codex-system skills to match new delegation rules
- [ ] Test Agent Teams workflow end-to-end with a real project
- [ ] Evaluate if gemini-explore agent should be removed or repurposed
- [ ] Update hooks for Agent Teams quality gates
- [x] Implement task sizing heuristic (file count + complexity + risk score) → `.claude/rules/adaptive-execution.md`
- [x] Define auto-escalation triggers and handoff checkpoints between XS/S/M/L → `.claude/rules/adaptive-execution.md`
- [ ] Add telemetry: initial size vs final size, escalation rate, cycle time, defect rate

## Open Questions

- [ ] Exact scoring threshold for XS vs S when risk is low but touching core files
- [ ] Should M tasks default to Claude direct, or 1 implementer by default?
- [ ] How to handle Compaction in long Agent Teams sessions?

## Changelog

| Date | Changes |
|------|---------|
| 2026-02-16 | Added adaptive execution sizing model (XS/S/M/L), hybrid classification principle, and runtime escalation policy |
| 2026-02-08 | Major redesign for Opus 4.6: 1M context, Agent Teams, skill pipeline |
| | Initial |
