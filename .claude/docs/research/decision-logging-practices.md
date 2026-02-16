# Decision Logging Practices Research

> Research findings on Architecture Decision Records (ADR) best practices,
> dual-logging patterns, and Japanese Linear comment templates for the
> Claude Code Orchestra workflow.

## 1. ADR Best Practices Summary

### Essential Metadata Fields

| Field | Necessity | Description |
|-------|-----------|-------------|
| **Title** | Essential | Short noun-phrase (e.g., "Use PostgreSQL for Session Storage") |
| **Status** | Essential | `proposed`, `accepted`, `rejected`, `deprecated`, `superseded` |
| **Date** | Essential | Date the decision was finalized |
| **Context** | Essential | Forces at play — technological, business, social constraints |
| **Decision** | Essential | The specific choice made |
| **Consequences** | Essential | Results — both positive (benefits) and negative (trade-offs) |
| **Options** | Recommended | Alternatives considered and why they were discarded |
| **Drivers** | Optional | Stakeholders or business goals driving the decision |

### Template Comparison

| Feature | Michael Nygard | MADR | Y-Statements |
|---------|---------------|------|--------------|
| Focus | Narrative & Context | Structured Trade-offs | Speed & Conciseness |
| Pros | Simple, easy to read | Forces "Considered Options" | Fits in tracker comments |
| Cons | May miss why alternatives were rejected | More verbose | Lacks detail for complex decisions |
| Best For | General architectural history | **Most Agile teams (recommended)** | Quick decisions, tracker summaries |

### Recommendation for This Project

Use a **hybrid approach**:
- **Local docs (log.md)**: MADR-inspired structured entries with PRE/DECISION/POST pattern
- **Linear comments**: Y-statement style concise summaries in Japanese
- **DESIGN.md**: Full MADR for major architectural decisions

This matches the existing architecture in DESIGN.md which already uses
PRE/DECISION/POST events with a local-first, batched Linear sync pattern.

### Traceability Across Phases

| Phase | Local Action | Tracker Action |
|-------|-------------|----------------|
| Plan (`/startproject`) | Save brief + decisions to `log.md` | POST sync: design summary comment |
| Implement (`/team-implement`) | Append decisions + summary to `log.md` | POST sync: implementation report comment |
| Review (`/team-review`) | Append review findings to `log.md` | POST sync: review results comment |
| Deploy (`/deploy`) | Append deploy record to `log.md` | POST sync: deploy info comment |

---

## 2. Dual-Logging Recommendations

### Core Philosophy: "Local-First, Tracker-Mirrored"

- **Repository** = source of truth for *technical reality* (what is built and why)
- **Tracker (Linear)** = source of truth for *work status* (who is doing what and when)

### Key Principles

1. **Link, Don't Copy**: If content > 10 lines, store in repo and link from tracker
2. **Snapshot Pattern**: Post immutable snapshots at phase transitions, not real-time sync
3. **Single Source for Decisions**: Technical decisions in repo, business decisions in tracker
4. **Phase Boundary Enforcement**: Log at phase transitions (PRE/POST checkpoints)

### What Goes Where

| Content | Linear (Team Visibility) | Local Docs (Developer Reference) |
|---------|------------------------|--------------------------------|
| Problem statement | Ticket description | `project-brief.md` |
| Design decisions | Phase summary comment | `DESIGN.md` + `log.md` |
| Implementation status | Commit + task summary | `implementation-summary.md` |
| Review findings | Critical/High summary | Full review reports in `research/` |
| Deploy info | Branch + commit links | `log.md` POST entry |

### Avoiding Duplication

- **Linear gets summaries** — concise Japanese comments at phase boundaries
- **Local gets details** — full structured records with all metadata
- **Cross-reference via artifacts** — Linear comments reference local file paths

### Completeness Checklists

Embed at each phase boundary:

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

---

## 3. Japanese Linear Comment Templates (9 Gaps)

All templates are fully in Japanese for Linear comments.
Placeholder variables use `{curly braces}`.

---

### Template 1: startproject Phase 1 — Project Brief (Gap 1)

**Trigger**: After creating the project brief (Phase 1, Step 4)

**Linear Comment**: Included in Phase 3 POST sync (not posted separately)

**Local Doc**: `.claude/docs/decisions/{feature}/project-brief.md`

```markdown
## プロジェクト概要書: {feature}

### 現状
- アーキテクチャ: {existing_architecture_summary}
- 関連コード: {key_files_and_modules}
- 既存パターン: {existing_patterns}

### 目標
{user_desired_outcome}

### スコープ
- 含める: {include_list}
- 除外する: {exclude_list}

### 制約
- {technical_constraints}
- {library_requirements}

### 成功基準
- {measurable_criteria}

### 作成日
{date}
```

---

### Template 2: startproject Phase 1 — Requirements Decisions (Gap 2)

**Trigger**: After requirements gathering (Phase 1, Step 3)

**Linear Comment**: Included in Phase 3 POST sync as part of "決定事項"

**Local Doc**: Appended to `.claude/docs/decisions/{feature}/log.md`

```markdown
### [startproject] DECISION — {date}

- **担当者**: ユーザー + Claude Lead
- **概要**: {requirement_decision}
- **理由**: {user_reasoning}
- **ステータス**: 承認済み
```

**Linear (Phase 3 POST にまとめて投稿)**:

```markdown
## 計画完了: {feature}

### 概要
{feature}の計画フェーズが完了しました。コードベース分析、要件定義、設計検討を経て、実装計画を策定しました。

### 要件定義の決定事項
- {requirement_decision_1}: {rationale_1}
- {requirement_decision_2}: {rationale_2}

### 設計方針
- アーキテクチャ: {architecture_decisions}
- 技術選定: {library_choices}
- パターン: {design_patterns}

### タスク分解
- {task_count}個のタスクに分割
- 推定ワークストリーム: {stream_count}本

### 成果物
- `.claude/docs/decisions/{feature}/project-brief.md`
- `.claude/docs/decisions/{feature}/log.md`
- `.claude/docs/DESIGN.md`（更新）
- `.claude/docs/research/{feature}.md`

### 次のステップ
- `/team-implement` で並列実装を開始
```

---

### Template 3: team-implement Step 0 — Design Decisions Record (Gap 3)

**Trigger**: After `/design-tracker` completes (Step 0)

**Linear Comment**:

```markdown
## 設計記録: {feature}

### アーキテクチャ
- {architecture_decision_1}
- {architecture_decision_2}

### 技術選定
| ライブラリ | 用途 | 選定理由 |
|-----------|------|---------|
| {library_1} | {role_1} | {rationale_1} |
| {library_2} | {role_2} | {rationale_2} |

### 主要な設計判断
| 判断 | 理由 | 代替案 | 日付 |
|------|------|--------|------|
| {decision_1} | {rationale_1} | {alternatives_1} | {date} |
| {decision_2} | {rationale_2} | {alternatives_2} | {date} |

### 参照ドキュメント
- `.claude/docs/DESIGN.md`
```

**Local Doc**: Appended to `.claude/docs/decisions/{feature}/log.md`

```markdown
### [team-implement] PRE — {date}

- **担当者**: Claude Lead
- **概要**: 実装フェーズ開始、設計決定を記録
- **成果物**: `.claude/docs/DESIGN.md`（design-tracker により更新）
```

---

### Template 4: team-implement Step 1 — Branch Creation Info (Gap 4)

**Trigger**: After feature branch creation (Step 1)

**Linear Comment**: Included in Step 5 POST sync (not posted separately)

**Local Doc**: Appended to `.claude/docs/decisions/{feature}/log.md`

```markdown
### [team-implement] DECISION — {date}

- **担当者**: Claude Lead（Gemini サブエージェント経由）
- **概要**: フィーチャーブランチ `feature/{feature_name}` を `{base_branch}` から作成
- **理由**: 標準フィーチャーブランチワークフロー
- **ステータス**: 承認済み
- **成果物**: ブランチ `feature/{feature_name}`
```

---

### Template 5: team-implement Steps 3-4 — Implementation Design Changes (Gap 5)

**Trigger**: When Lead makes intervention decisions during monitoring

**Linear Comment**: Included in Step 5 POST sync as part of "実装中の決定事項"

**Local Doc**: Appended to `.claude/docs/decisions/{feature}/log.md`

```markdown
### [team-implement] DECISION — {date}

- **担当者**: Claude Lead
- **概要**: {intervention_description}
- **理由**: {intervention_rationale}
- **ステータス**: 承認済み
```

**Intervention triggers for recording**:
- File ownership reassignment
- Teammate re-instruction
- Technical problem resolution (especially Codex consultations)
- Scope changes during implementation

---

### Template 6: team-implement Step 5 — Implementation Complete Report, Local Doc (Gap 6)

**Trigger**: After integration verification (Step 5)

**Linear Comment** (already defined in SKILL.md, enhanced):

```markdown
## 実装完了: {feature}

### コミット履歴
- [{commit_hash_1}]({commit_url_1}): {commit_message_1}
- [{commit_hash_2}]({commit_url_2}): {commit_message_2}

### 完了タスク
- [x] {task_1}
- [x] {task_2}

### 品質チェック結果
| チェック | 結果 |
|---------|------|
| ruff | {pass_or_fail} |
| ty | {pass_or_fail} |
| pytest | {test_count}件通過、カバレッジ {coverage}% |

### 実装中の決定事項
- {decision_1}: {rationale_1}
- {decision_2}: {rationale_2}

### 変更ファイル
- {file_list}

### 次のステップ
- `/team-review` で並列レビュー予定
```

**Local Doc**: `.claude/docs/decisions/{feature}/implementation-summary.md`

```markdown
## Implementation Summary: {feature}

### Completed Tasks
- [x] {task_1}
- [x] {task_2}

### Quality Checks
- ruff: {pass_or_fail}
- ty: {pass_or_fail}
- pytest: {test_count} tests, {coverage}% coverage

### Commits
- {hash_1}: {message_1}
- {hash_2}: {message_2}

### Key Decisions During Implementation
- {decision_1}: {rationale_1}

### Changed Files
- {file_list}

### Date
{date}
```

**Log entry**: Appended to `.claude/docs/decisions/{feature}/log.md`

```markdown
### [team-implement] POST — {date}

- **担当者**: Claude Lead
- **概要**: 実装完了、{task_count}タスク完了、品質チェック全通過
- **成果物**: `.claude/docs/decisions/{feature}/implementation-summary.md`
```

---

### Template 7: team-review Steps 3-4 — Review Results (Gap 7)

**Trigger**: After synthesizing review results and presenting to user (Step 4)

**Linear Comment**:

```markdown
## レビュー結果: {feature}

### サマリー
| カテゴリ | 件数 | 内訳 |
|---------|------|------|
| セキュリティ | {security_count}件 | Critical: {n}, High: {n}, Medium: {n} |
| コード品質 | {quality_count}件 | High: {n}, Medium: {n}, Low: {n} |
| テストカバレッジ | {coverage}% | 目標80%に対して{above_or_below} |
| Simplify対象 | {simplify_count}件 | Small: {n}, Medium: {n}, Large: {n} |

### Critical / High 発見事項
- [{severity}] {issue_title}: {description} → 修正案: {fix}

### 推奨アクション
1. {action_1}
2. {action_2}

### レビュー詳細ドキュメント
- `.claude/docs/research/review-security-{feature}.md`
- `.claude/docs/research/review-quality-{feature}.md`
- `.claude/docs/research/review-tests-{feature}.md`
- `.claude/docs/research/review-simplify-{feature}.md`

### 次のステップ
- Critical/High の修正完了後、`/deploy` へ進行
```

**Local Doc**: Appended to `.claude/docs/decisions/{feature}/log.md`

```markdown
### [team-review] POST — {date}

- **担当者**: Claude Lead
- **概要**: レビュー完了 — Critical {n}件、High {n}件の発見事項
- **成果物**: `.claude/docs/research/review-*-{feature}.md`
```

---

### Template 8: team-review Step 5 — Simplify Results (Gap 8)

**Trigger**: After simplify refactoring completion (Step 5)

**Linear Comment** (appended to review comment or new comment):

```markdown
### Simplify 完了: {feature}

### 変更内容
| # | ファイル | 変更内容 | テスト結果 |
|---|---------|----------|-----------|
| 1 | `{file_1}` | {change_description_1} | 通過 |
| 2 | `{file_2}` | {change_description_2} | 通過 |

### スキップした項目
- {skipped_item}: {skip_reason}

### 承認済み対象
- ユーザーが承認した番号: {selected_numbers}
```

**Local Doc**: Appended to `.claude/docs/decisions/{feature}/log.md`

```markdown
### [team-review] DECISION — {date}

- **担当者**: Claude Lead
- **概要**: Simplify リファクタリングを {file_count}ファイルに適用
- **理由**: ユーザーが Simplify 対象 #{selected_numbers} を承認
- **ステータス**: 承認済み
- **成果物**: 変更ファイル一覧は下記参照
```

---

### Template 9: deploy Step 4 — Deploy Complete, Local Doc (Gap 9)

**Trigger**: After pushing to remote and returning to original branch (Step 4)

**Linear Comment** (already defined in SKILL.md, kept as-is):

```markdown
## デプロイ: {feature}

### ブランチ
- [`feature/{feature_name}`]({branch_url}) → origin に push 済み

### コミット履歴
- [{commit_hash_1}]({commit_url_1}): {commit_message_1}
- [{commit_hash_2}]({commit_url_2}): {commit_message_2}

### レビュー結果サマリー
- セキュリティ: {security_summary}
- コード品質: {quality_summary}
- テストカバレッジ: {coverage_summary}

### 次のステップ
- PR 作成 / マージ待ち
```

**Local Doc**: Appended to `.claude/docs/decisions/{feature}/log.md`

```markdown
### [deploy] POST — {date}

- **担当者**: Claude Lead（Gemini サブエージェント経由）
- **概要**: フィーチャーブランチを origin に push、{original_branch} に復帰
- **成果物**: ブランチ `feature/{feature_name}` on origin

### デプロイ詳細
- ブランチ: `feature/{feature_name}` → origin
- コミット数: {commit_count}件
- レビュー状況: Critical/High 発見事項は解決済み
- Linear: コメント投稿済み
```

---

## 4. Local Doc Save Patterns (File Paths and Content Structure)

### Directory Structure

```
.claude/docs/decisions/{feature}/
  ├── log.md                      # Canonical append-only decision log (all phases)
  ├── project-brief.md            # Phase 1 output (startproject Step 4)
  └── implementation-summary.md   # Phase 4 output (team-implement Step 5)
```

### Pattern Summary

| Gap # | Phase | Local File | Content |
|-------|-------|-----------|---------|
| 1 | startproject Phase 1 | `decisions/{feature}/project-brief.md` | Full project brief |
| 2 | startproject Phase 1 | `decisions/{feature}/log.md` (DECISION) | Requirements decisions |
| 3 | team-implement Step 0 | `decisions/{feature}/log.md` (PRE) | Design snapshot reference |
| 4 | team-implement Step 1 | `decisions/{feature}/log.md` (DECISION) | Branch creation info |
| 5 | team-implement Steps 3-4 | `decisions/{feature}/log.md` (DECISION) | Implementation interventions |
| 6 | team-implement Step 5 | `decisions/{feature}/implementation-summary.md` + `log.md` (POST) | Full implementation report |
| 7 | team-review Steps 3-4 | `decisions/{feature}/log.md` (POST) | Review results summary |
| 8 | team-review Step 5 | `decisions/{feature}/log.md` (DECISION) | Simplify results |
| 9 | deploy Step 4 | `decisions/{feature}/log.md` (POST) | Deploy record |

### Log Entry Format

All entries in `log.md` follow this structure:

```markdown
### [{phase}] {event_type} — {date}

- **担当者**: {actor}
- **概要**: {one_line_summary}
- **理由**: {rationale} (DECISION events only)
- **ステータス**: {proposed | accepted | rejected | deferred} (DECISION events only)
- **成果物**: {artifact_list}

{optional_details}
```

### Linear Sync Strategy

| Phase | Linear Timing | Comment Count |
|-------|--------------|---------------|
| startproject | Phase 3 POST (one comment includes brief + requirements + design) | 1 |
| team-implement | Step 0 POST (design) + Step 5 POST (implementation) | 2 |
| team-review | Step 4 POST (review results) + Step 5 POST (simplify, if done) | 1-2 |
| deploy | Step 4 POST (deploy info) | 1 |

**Total per feature lifecycle**: 5-6 Linear comments, each a coherent phase summary.

---

## 5. Sources

- Michael Nygard's original ADR article (Cognitect, 2011)
- MADR (Markdown Any Decision Records) — https://adr.github.io/madr/
- ThoughtWorks Technology Radar: Lightweight ADRs
- Y-Statements pattern for concise decision summaries
- Dual-logging research via Gemini CLI (2026-02-16)
