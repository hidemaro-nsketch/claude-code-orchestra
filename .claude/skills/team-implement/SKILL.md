---
name: team-implement
description: |
  Parallel implementation using Agent Teams. Spawns teammates per module/layer,
  each owning separate files to avoid conflicts. Uses shared task list with
  dependencies for autonomous coordination. Run after /startproject plan approval.
metadata:
  short-description: Parallel implementation with Agent Teams
---

# Team Implement

**Agent Teams による並列実装。`/startproject` で承認された計画に基づいて実行する。**

## Prerequisites

- `/startproject` が完了し、計画がユーザーに承認されていること
- `.claude/docs/DESIGN.md` にアーキテクチャが記録されていること
- タスクリストが作成されていること
- `/startproject` Phase 1 で取得した **Linear タスクID** が引き継がれていること

## Workflow

```
Step 1: Analyze Plan & Design Team
  計画からタスク依存関係を分析し、チーム構成を決定
    ↓
Step 2: Spawn Agent Team
  モジュール/レイヤー単位でTeammateを起動
    ↓
Step 3: Monitor & Coordinate
  Lead がモニタリング、統合、品質管理
    ↓
Step 4: Integration & Verification
  全タスク完了後、統合テスト実行
```

---

## Step 0: Create Feature Branch

**作業開始前に feature ブランチを作成する。**

```
Step 1: 現在のブランチを記録（deploy 時に戻る先）
  git branch --show-current → 保持しておく

Step 2: feature ブランチを作成・チェックアウト
  git checkout -b feature/{feature-name}
```

> **Routing**: git 操作は `.claude/rules/tool-routing.md` に従い、Gemini サブエージェント経由で実行する。

ブランチ名の `{feature-name}` は `/startproject` で指定された機能名をケバブケースに変換して使用する（例: `feature/user-authentication`）。

---

## Step 1: Analyze Plan & Design Team

**タスクリストから並列化可能なワークストリームを特定する。**

### Team Design Principles

1. **ファイル所有権の分離**: 各Teammateが異なるファイルセットを所有
2. **依存関係の尊重**: 依存タスクは同一Teammateか、依存順で実行
3. **適切な粒度**: Teammate あたり 5-6 タスクが目安

### Common Team Patterns

**Pattern A: Module-Based (推奨)**
```
Teammate 1: Module A (models, core logic)
Teammate 2: Module B (API, endpoints)
Teammate 3: Tests (unit + integration)
```

**Pattern B: Layer-Based**
```
Teammate 1: Data layer (models, DB)
Teammate 2: Business logic (services)
Teammate 3: Interface layer (API/CLI)
```

**Pattern C: Feature-Based**
```
Teammate 1: Feature X (all layers)
Teammate 2: Feature Y (all layers)
Teammate 3: Shared infrastructure
```

### Anti-patterns

- 2つの Teammate が同じファイルを編集 → 上書きリスク
- Teammate あたりのタスクが多すぎる → 長時間放置リスク
- 依存関係が複雑すぎる → 調整コストが利益を上回る

---

## Step 2: Spawn Agent Team

**計画に基づいてチームを起動する。**

```
Create an agent team for implementing: {feature}

Each teammate receives:
- Project Brief from CLAUDE.md
- Architecture from .claude/docs/DESIGN.md
- Library constraints from .claude/docs/libraries/
- Their specific task assignments

Spawn teammates:

1. **Implementer-{module}** for each module/workstream
   Prompt: "You are implementing {module} for project: {feature}.

   Read these files for context:
   - CLAUDE.md (project context)
   - .claude/docs/DESIGN.md (architecture)
   - .claude/docs/libraries/ (library constraints)

   Your assigned tasks:
   {task list for this teammate}

   Your file ownership:
   {list of files this teammate owns}

   Rules:
   - ONLY edit files in your ownership set
   - Follow existing codebase patterns
   - Write type hints on all functions
   - Run ruff check after each file change
   - Communicate with other teammates if you need interface changes

   When done with each task, mark it completed in the task list."

2. **Tester** (optional but recommended)
   Prompt: "You are the Tester for project: {feature}.

   Read:
   - CLAUDE.md, .claude/docs/DESIGN.md
   - Existing test patterns in tests/

   Your tasks:
   - Write tests for each module as implementers complete them
   - Follow TDD where possible (write test stubs first)
   - Run uv run pytest after each test file
   - Report failing tests to the relevant implementer

   Test coverage target: 80%+"

Use delegate mode (Shift+Tab) to prevent Lead from implementing directly.
Wait for all teammates to complete their tasks.
```

---

## Step 3: Monitor & Coordinate

**Lead は実装せず、モニタリングと統合に専念する。**

### Monitoring Checklist

- [ ] タスクリストの進捗を確認（Ctrl+T）
- [ ] 各 Teammate の出力を確認（Shift+Up/Down）
- [ ] ファイル競合がないか確認
- [ ] 行き詰まっている Teammate がいないか確認

### Intervention Triggers

| 状況 | 対応 |
|------|------|
| Teammate が長時間タスクを進めない | メッセージで確認、必要なら再指示 |
| ファイル競合が発生 | 所有権を再配分 |
| テストが失敗し続ける | 関連する Implementer にメッセージ |
| 想定外の技術的問題 | Codex に相談（サブエージェント経由） |

### Quality Gates (via Hooks)

`TeammateIdle` hook と `TaskCompleted` hook が自動で品質チェック：

- lint チェック（ruff）
- テスト実行（pytest）
- 型チェック（ty）

---

## Step 4: Integration & Verification

**全タスク完了後、統合検証を行う。**

```bash
# All quality checks
uv run ruff check .
uv run ruff format --check .
uv run ty check src/
uv run pytest -v

# Or via poe
poe all
```

### Integration Report

```markdown
## 実装完了: {feature}

### 完了タスク
- [x] {task 1}
- [x] {task 2}
...

### 品質チェック
- ruff: ✓ / ✗
- ty: ✓ / ✗
- pytest: ✓ ({N} tests passed)
- coverage: {N}%

### 次のステップ
`/team-review` で並列レビューを実行してください
```

### Post Completion to Linear

実装完了後、Linear タスクに作業内容をコメントとして追加する：

```
Step 1: GitHub MCP ツールでコミット情報・変更ファイルを取得
  - feature/{feature-name} ブランチのコミット履歴
  - 各コミットのハッシュ、メッセージ、URL
  - 変更ファイル一覧

Step 2: Linear MCP ツールで、/startproject から引き継いだ Linear タスクIDに以下をコメント:

## 実装完了: {feature}

### コミット履歴
- [{commit hash 1}]({commit URL 1}): {commit message 1}
- [{commit hash 2}]({commit URL 2}): {commit message 2}
...

### 完了タスク
- [x] {task 1}
- [x] {task 2}
...

### 品質チェック結果
- ruff: ✓ / ✗
- ty: ✓ / ✗
- pytest: {N} tests passed, coverage {N}%

### 変更ファイル
- {file list from GitHub MCP}

### 次のステップ
`/team-review` で並列レビュー予定
```

> **Routing**: `.claude/rules/tool-routing.md` に従い、GitHub MCP でコミット情報取得、Linear MCP でコメント投稿。

### Cleanup

```
Clean up the team
```

---

## Tips

- **Delegate mode**: Shift+Tab で Lead が実装を避ける
- **タスク粒度**: Teammate あたり 5-6 タスクが最適
- **ファイル競合回避**: モジュール単位の所有権分離が最重要
- **Tester 分離**: Implementer とは別に Tester を立てるとTDD的に回る
- **コスト意識**: 各 Teammate は独立した Claude インスタンス（トークン消費大）
