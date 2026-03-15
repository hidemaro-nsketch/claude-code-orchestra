---
name: team-review
description: |
  Parallel code review using Agent Teams. Spawns specialized reviewers
  (security, quality, test coverage) to review implementation from
  different perspectives simultaneously. Run after implementation.
context: fork
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Agent, AskUserQuestion, SendMessage, TaskCreate, TaskUpdate, TaskList, TaskGet, TodoWrite, ToolSearch
metadata:
  short-description: Parallel review with Agent Teams
---

# Team Review

**Agent Teams による並列レビュー。実装完了後に複数の視点から同時にレビューする。**

## Prerequisites

- 実装が完了していること（`/team-implement` 後、または手動実装後）
- 全テストが通過していること

## Adaptive Execution

> 参照: `.claude/rules/adaptive-execution.md`

タスクサイズに応じてレビュー方式を適応させる：

| Tier | レビュー方式 | レビュアー数 |
|------|------------|------------|
| **XS** | レビュー省略 | 0 |
| **S** | Claude が直接レビュー（単一パス） | 0（チームなし） |
| **M** | 2 レビュアー（Security + Quality） | 2 |
| **L** | フル 4 レビュアー | 4（Security, Quality, Test, Simplify） |

**XS の場合**: レビューをスキップ。
**S の場合**: Claude Lead が変更差分を読み、セキュリティと品質を単一パスで確認。Step 2-3 をスキップし、直接 Step 4（結果報告 + ログ記録）→ Step 5（自動修正判定）。
**M の場合**: Security Reviewer + Quality Reviewer の 2 名のみ起動。Step 4 のログ記録は必須。
**L の場合**: フルワークフロー（4 レビュアー）。全記録ステップ必須。

### 記録ステップの適用範囲（MUST）

**以下の記録は該当 tier で必須。スキップ不可。**

| 記録アクション | 発生箇所 | XS | S | M | L |
|---------------|---------|:--:|:--:|:--:|:--:|
| `log-{feature}.md` POST エントリ（レビュー結果） | Step 4 | — | MUST | MUST | MUST |
| `fix-tasks-{feature}.md` 保存（修正タスク） | Step 5 | — | 該当時 | 該当時 | 該当時 |
| `log-{feature}.md` DECISION エントリ（Simplify結果） | Step 6 | — | 該当時 | 該当時 | 該当時 |

## Workflow (Full — Tier L)

```
Step 1: Gather Diff
  実装範囲の変更差分を収集
    ↓
Step 2: Spawn Review Team
  専門レビュアーを並列起動
    ↓
Step 3: Synthesize Findings
  レビュー結果を統合、優先度付け
    ↓
Step 4: Report to User
  4-1. 発見事項 + simplify 対象を提示
  4-2. [MUST] レビュー結果をログに記録
    ↓
Step 5: Auto-Fix Loop
  5-1. Medium+ 発見事項を判定
  5-2. ラウンド上限チェック（最大2ラウンド）
  5-3. 修正タスク保存 → /team-implement 自動起動
    ↓ Medium+ なし or ラウンド上限到達
Step 6: Simplify (Optional)
  6-1. 承認された箇所をリファクタリング
  6-2. [MUST] Simplify 結果をログに記録（実行した場合）
    ↓
Step 7: Auto-Continue to Deploy
  7-1. /deploy を自動起動
```

---

## Step 1: Gather Diff

**レビュー対象の変更範囲を特定する。**

```bash
# All changes from main branch
git diff main...HEAD

# Changed files list
git diff main...HEAD --name-only

# Commit history
git log main..HEAD --oneline
```

---

## Step 2: Spawn Review Team

**専門的な視点を持つレビュアーを並列起動する。**

```
Create an agent team to review implementation of: {feature}

The following files were changed:
{changed files list}

Spawn reviewers:

1. **Security Reviewer**
   Prompt: "You are a Security Reviewer for: {feature}.

   Review all changed files for security vulnerabilities:
   - Hardcoded secrets or credentials
   - SQL injection, XSS, command injection
   - Input validation gaps
   - Authentication/authorization issues
   - Sensitive data exposure in logs/errors
   - Dependency vulnerabilities

   Changed files: {list}

   Reference: .claude/rules/security.md

   For each finding:
   - Severity: Critical / High / Medium / Low
   - File and line number
   - Description of the issue
   - Recommended fix

   Save report to .claude/docs/research/review-security-{feature}.md"

2. **Quality Reviewer**
   Prompt: "You are a Quality Reviewer for: {feature}.

   Review all changed files for code quality:
   - Adherence to coding principles (.claude/rules/coding-principles.md)
   - Single responsibility violations
   - Deep nesting (should use early return)
   - Missing type hints
   - Magic numbers
   - Naming clarity
   - Function length (target < 20 lines)
   - Library constraint violations (.claude/docs/libraries/)

   Use OpenCode CLI for deep analysis of complex logic:
   opencode run -m github-copilot/gpt-5.4 "{question}" 2>/dev/null

   Changed files: {list}

   For each finding:
   - Severity: High / Medium / Low
   - File and line number
   - Current code
   - Suggested improvement

   Save report to .claude/docs/research/review-quality-{feature}.md"

3. **Test Reviewer**
   Prompt: "You are a Test Reviewer for: {feature}.

   Review test coverage and quality:
   - Run: uv run pytest --cov=src --cov-report=term-missing
   - Check: Are all happy paths tested?
   - Check: Are error cases covered?
   - Check: Are boundary values tested?
   - Check: Are edge cases handled?
   - Check: Are external deps properly mocked?
   - Check: Do tests follow AAA pattern?
   - Check: Are tests independent (no order dependency)?

   Reference: .claude/rules/testing.md

   For each gap:
   - File/function missing coverage
   - What test cases are needed
   - Priority: High / Medium / Low

   Save report to .claude/docs/research/review-tests-{feature}.md"

4. **Simplify Reviewer**
   Prompt: "You are a Simplify Reviewer for: {feature}.

   Analyze all changed files for structural complexity that can be simplified
   WITHOUT changing behavior (refactoring only).

   Look for:
   - Deep nesting (depth > 2) → early return candidates
   - Long functions (> 20 lines) → extract function candidates
   - Unclear naming → rename candidates
   - Missing type hints → annotation candidates
   - Magic numbers → constant extraction candidates
   - Mutable patterns → immutable alternatives

   Changed files: {list}

   References:
   - .claude/rules/coding-principles.md
   - .claude/docs/libraries/ (preserve library constraints)

   For each finding:
   - File and line number
   - Current code snippet (brief)
   - Proposed refactoring (brief)
   - Effort: Small / Medium / Large
   - Risk: Low / Medium (behavior change risk)

   IMPORTANT: Only include refactorings that preserve existing behavior.
   Skip anything that would change functionality.

   Save report to .claude/docs/research/review-simplify-{feature}.md"

Wait for all reviewers to complete.
```

### Optional: Competing Hypotheses (for debugging)

For bug investigation, add adversarial reviewers:

```
Spawn 3-5 teammates with different hypotheses about the bug.
Have them actively try to disprove each other's theories.
```

---

## Step 3: Synthesize Findings

**全レビュアーの結果を統合し、優先度付けする。**

Read review reports:
- `.claude/docs/research/review-security-{feature}.md`
- `.claude/docs/research/review-quality-{feature}.md`
- `.claude/docs/research/review-tests-{feature}.md`
- `.claude/docs/research/review-simplify-{feature}.md`

### Prioritization

| Priority | Criteria | Action |
|----------|----------|--------|
| **Critical** | Security vulnerabilities, data loss risk | Must fix before merge |
| **High** | Bugs, missing critical tests, type errors | Should fix before merge |
| **Medium** | Code quality, naming, patterns | Fix if time allows |
| **Low** | Style, minor improvements | Track for later |

---

## Step 4: Report to User

**統合レビュー結果をユーザーに提示する（日本語）。**

```markdown
## レビュー結果: {feature}

### サマリー
- セキュリティ: {N}件 (Critical: {n}, High: {n}, Medium: {n})
- コード品質: {N}件 (High: {n}, Medium: {n}, Low: {n})
- テストカバレッジ: {N}% (目標80%に対して {above/below})
- Simplify: {N}件 (Small: {n}, Medium: {n}, Large: {n})

### Critical / High 発見事項

#### [{Severity}] {Issue Title}
- **ファイル**: `{file}:{line}`
- **問題**: {description}
- **修正案**: {recommended fix}

...

### 推奨アクション
1. {Action 1 — Critical fix}
2. {Action 2 — High priority fix}
3. {Action 3 — Test gap to fill}

### Medium / Low 発見事項
{Brief list — details in review reports}

### Simplify 対象
Simplify Reviewer のレポートから、リファクタリング可能な箇所:

| # | ファイル | 問題 | 改善内容 |
|---|---------|------|----------|
| 1 | `{file}:{line}` | {e.g., deep nesting} | {e.g., early return に変換} |
| 2 | `{file}:{line}` | {e.g., long function} | {e.g., 関数抽出} |
...

---
**Note**: Critical/High/Medium の発見事項は Step 5 で自動修正されます。
Simplify はすべての自動修正完了後（Step 6）に提案されます。
```

### Cleanup

```
Clean up the team
```

### 4-2. [MUST] レビュー結果をログに記録

**このサブステップは S/M/L tier で必須。スキップ不可。**

レビュー結果をローカルログに記録する：

`.claude/docs/decisions/log-{feature}.md` に POST エントリを追記:

```markdown
### [team-review] POST — {date}

- **担当者**: Claude Lead
- **概要**: レビュー完了 — Critical {n}件、High {n}件の発見事項
- **成果物**: `.claude/docs/research/review-*-{feature}.md`

### レビューサマリー
- セキュリティ: {security_count}件 (Critical: {n}, High: {n}, Medium: {n})
- コード品質: {quality_count}件 (High: {n}, Medium: {n}, Low: {n})
- テストカバレッジ: {coverage}% (目標80%に対して {above/below})
- Simplify対象: {simplify_count}件
```

---

## Step 5: Auto-Fix Loop (Medium+ Findings)

**リスク「中」以上の発見事項がある場合、自動的に `/team-implement` に戻って修正する。**

> このステップにより、team-review → team-implement → team-review の自動修正ループが実現する。

### 5-1. 修正対象の判定

Step 3 の統合結果から、以下の条件で自動修正対象を判定する：

| Priority | 自動修正 | 理由 |
|----------|---------|------|
| **Critical** | ✓ 自動修正 | セキュリティ脆弱性、データ損失リスク |
| **High** | ✓ 自動修正 | バグ、重要テスト欠如、型エラー |
| **Medium** | ✓ 自動修正 | コード品質、命名、パターン |
| **Low** | ✗ スキップ | スタイル、軽微な改善（記録のみ） |

### 5-2. ループ制限

**最大 2 ラウンドまで**。無限ループを防止する。

- **Round 1**: 初回レビューで Medium+ 発見 → team-implement で修正 → 再レビュー
- **Round 2**: 再レビューでまだ Medium+ 残存 → team-implement で修正 → 再レビュー
- **Round 3 以降**: 自動修正を中止し、残存する発見事項をユーザーに報告

ラウンド数は `.claude/docs/decisions/log-{feature}.md` の `[team-review] POST` エントリ数で判定する。

### 5-3. 修正タスクの作成

Medium+ の発見事項を修正タスクリストに変換し、ファイルに保存する：

`.claude/docs/decisions/fix-tasks-{feature}.md`:

```markdown
## Fix Tasks from Review Round {N}: {feature}

### Source
- Review round: {N}
- Date: {date}

### Tasks

#### [Critical] {Issue Title}
- **ファイル**: `{file}:{line}`
- **問題**: {description}
- **修正方針**: {recommended fix}

#### [High] {Issue Title}
- **ファイル**: `{file}:{line}`
- **問題**: {description}
- **修正方針**: {recommended fix}

#### [Medium] {Issue Title}
- **ファイル**: `{file}:{line}`
- **問題**: {description}
- **修正方針**: {recommended fix}
```

### 5-4. 実行手順

1. **Medium+ 発見事項がない場合**: 「レビュー完了、修正不要な発見事項なし」と報告 → Step 6（Simplify）に進む
2. **Medium+ 発見事項があり、ラウンド数 ≤ 2 の場合**:
   - 修正タスクファイルを保存
   - ユーザーに修正ラウンド開始を報告
   - `/team-implement` を自動起動（修正モード）
3. **Medium+ 発見事項があり、ラウンド数 > 2 の場合**:
   - 残存する発見事項をユーザーに報告
   - 「自動修正の上限（2ラウンド）に達しました。残りの発見事項は手動で対応してください。」と報告
   - Step 6（Simplify）に進む

```
修正が必要な発見事項が {N}件 あります（Critical: {n}, High: {n}, Medium: {n}）。
自動修正ラウンド {round} を開始します。`/team-implement` で修正を実行します。
```

**重要**: ユーザーに「修正しますか？」と質問せず、自動的に `/team-implement` を起動すること。`team-implement → team-review` と同様の自動発火パターンに従う。

---

## Step 6: Simplify (User-Approved)

**ユーザーが承認した simplify 対象に対してリファクタリングを実行する。**

> Step 4 でユーザーが simplify 対象を承認（番号指定 or 全承認）した場合のみ実行。

### Workflow

1. **承認された対象を確認** — ユーザーが選んだ番号 or "全部"
2. **対象ファイルを読む** — 現在のコードを確認
3. **ライブラリ制約チェック** — `.claude/docs/libraries/` を参照
4. **リファクタリング実行** — simplify の原則に従う:
   - Early return（深いネストの解消）
   - Extract function（長い関数の分割）
   - Clear naming（不明瞭な命名の修正）
   - Type hints 追加
5. **テスト実行** — 各変更後に `uv run pytest -v` で動作確認
6. **結果報告** — 変更内容のサマリーをユーザーに提示

### Simplify Principles (from /simplify)

| 原則 | 基準 |
|------|------|
| Single Responsibility | 1 function = 1 thing |
| Short Functions | 20行以下を目標 |
| Shallow Nesting | depth ≤ 2、early return 活用 |
| Clear Naming | コメント不要な明確さ |
| Type Hints | 全関数に必須 |

### Output

```markdown
## Simplify 完了

### 変更内容
| # | ファイル | 変更 | テスト |
|---|---------|------|--------|
| 1 | `{file}` | {what changed} | ✓ pass |
| 2 | `{file}` | {what changed} | ✓ pass |

### スキップ
- {skipped items with reason, if any}
```

> **Note**: simplify は動作を変えないリファクタリングのみ。機能変更を伴う修正は Critical/High の修正ステップで対応する。

### 6-2. [MUST] Simplify 結果をログに記録

**Simplify を実行した場合、このサブステップは必須。スキップ不可。**

Simplify 完了後、結果をローカルログに記録する：

`.claude/docs/decisions/log-{feature}.md` に DECISION エントリを追記:

```markdown
### [team-review] DECISION — {date}

- **担当者**: Claude Lead
- **概要**: Simplify リファクタリングを {file_count}ファイルに適用
- **理由**: ユーザーが Simplify 対象 #{selected_numbers} を承認
- **ステータス**: 承認済み
- **成果物**: 変更ファイル一覧は下記参照

### Simplify 詳細
| # | ファイル | 変更内容 | テスト結果 |
|---|---------|----------|-----------|
| 1 | `{file}` | {change_description} | 通過 |
```

---

## Step 7: Auto-Continue to Deploy

**レビューループおよび Simplify 完了後、自動的に `/deploy` を起動する。**

> このステップにより、team-review → deploy の自動発火が実現する。

### 7-1. 実行手順

Step 5（Auto-Fix Loop）と Step 6（Simplify）の完了後：

1. **XS の場合**: team-review 自体がスキップされるため、このステップは実行されない（team-implement Step 6 から直接 `/deploy` が起動される）
2. **S/M/L の場合**: `/deploy` スキルを自動起動する

```
レビューが完了しました。続けて `/deploy` でデプロイを実行します。
```

**重要**: ユーザーに「デプロイしますか？」と質問せず、自動的に `/deploy` を起動すること。`team-implement → team-review` と同様の自動発火パターンに従う。

---

## Tips

- **Adaptive**: XS はスキップ、S は Claude 直接、M は 2 名、L はフル 4 名（`.claude/rules/adaptive-execution.md`）
- **レビュアーの専門分化**: 各レビュアーが異なる視点に集中することで漏れを防ぐ（Tier L）
- **OpenCode 活用**: Quality Reviewer が複雑なロジックを OpenCode に分析させる
- **レポート永続化**: `.claude/docs/research/` にレビュー結果を保存し、修正時の参照に
- **競合仮説モード**: バグ調査時は adversarial review パターンが有効
- **自動修正ループ**: Medium+ の発見事項は自動的に team-implement で修正される（最大 2 ラウンド）
- **自動デプロイ**: レビュー完了後、自動的に `/deploy` が起動される
- **コスト意識**: 4 レビュアー = 4x トークン消費 → タスクサイズに合わせてレビュアー数を調整
