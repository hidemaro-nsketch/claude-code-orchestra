---
name: deploy
description: |
  Git operations skill. Handles both workflow deploys (push, PR, branch cleanup)
  and ad-hoc git operations (commit, log, diff, branch, etc.).
  All git operations are routed through this skill for context isolation.
context: fork
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion, ToolSearch, mcp__linear-server__save_comment, mcp__linear-server__get_issue, mcp__linear-server__save_issue, mcp__linear-server__list_issue_statuses
metadata:
  short-description: All git operations - deploy workflow and ad-hoc git commands
---

# Deploy

**全ての git 操作を担当するスキル。デプロイワークフローとアドホック git 操作の両方をカバーする。**

## Two Modes

このスキルは 2 つのモードで動作する:

| モード | 発動条件 | 内容 |
|--------|---------|------|
| **Deploy Workflow** | `/team-review` 完了後、PR 作成・push 要求時 | フル deploy フロー（Step 1-5） |
| **Ad-hoc Git** | アドホックな git 操作要求時 | ユーザーが指定した git 操作を直接実行 |

### モード判定ロジック

```
1. ユーザーの要求を分析
2. デプロイワークフロー（PR作成 + push + Linear投稿）の意図がある場合 → Deploy Workflow モード
3. 単発の git 操作（commit, log, diff, branch, blame 等）の意図がある場合 → Ad-hoc Git モード
4. 不明な場合 → ユーザーに確認
```

---

## Ad-hoc Git Mode

**ユーザーが指定した git 操作を `context: fork` の分離コンテキストで直接実行する。**

### 対応する操作

| 操作カテゴリ | コマンド例 |
|-------------|-----------|
| **コミット** | `git add`, `git commit` |
| **ブランチ** | `git branch`, `git checkout`, `git switch`, `git merge` |
| **履歴参照** | `git log`, `git diff`, `git show`, `git blame` |
| **リモート** | `git push`, `git pull`, `git fetch` |
| **その他** | `git stash`, `git rebase`, `git cherry-pick`, `git tag` |

### 実行手順

1. ユーザーの要求を解釈し、必要な git コマンドを特定する
2. 実行前に現在のブランチ・状態を `git status` と `git branch --show-current` で確認
3. git コマンドを実行する
4. 結果を日本語で簡潔に報告する

### 注意事項

- **破壊的操作**（`git reset --hard`, `git push --force`, `git clean -f` 等）はユーザーに確認してから実行する
- コミットメッセージはユーザーが指定しない場合、変更内容に基づいて適切に生成する
- Linear 投稿や Decision Log 更新は行わない（Deploy Workflow モードのみ）

---

## Deploy Workflow Mode

**feature ブランチを push し、PR を作成して、元のブランチに戻る。**

### Prerequisites

- `/team-implement` で feature ブランチが作成されていること
- `/team-review` が完了していること
- すべての品質チェックがパスしていること

## Workflow

```
Step 1: 品質チェック確認
  ↓
Step 2: feature ブランチを push
  ↓
Step 3: PR を作成（gh CLI 経由）
  ↓
Step 4: 元のブランチに戻る
  ↓
Step 5: デプロイ情報を記録・投稿
  5-1. [MUST] Linear タスクにデプロイ情報をコメント
  5-2. [MUST] Linear タスクのステータスを "In Review" に変更
  5-3. [MUST] ローカルログに POST エントリ追記
```

### 記録ステップの適用範囲（MUST）

**以下の記録・投稿は必須。スキップ不可。**

| 記録アクション | 発生箇所 |
|---------------|---------|
| Linear にデプロイ情報コメント | Step 5-1 |
| Linear ステータスを "In Review" に変更 | Step 5-2 |
| タスクファイルの Decision Log セクション | Step 5-3 |

> **Linear タスクIDが無い場合**: ユーザーに確認する。「Linear タスクIDが見つかりません。IDを指定しますか？スキップしますか？」と質問し、指示に従う。**暗黙的なスキップは禁止。**

---

## Step 1: Pre-push Verification

push 前に最終確認を行う：

```bash
# Uncommitted changes がないか確認
git status

# 品質チェック
uv run ruff check .
uv run ruff format --check .
uv run pytest -v
```

未コミットの変更がある場合はユーザーに確認する。

## Step 2: Push Feature Branch

```bash
# 現在のブランチ名を確認
git branch --show-current
# → feature/{feature-name} であることを確認

# リモートに push
git push -u origin feature/{feature-name}
```

## Step 3: Create Pull Request (gh CLI)

> **重要**: PR 作成には `gh` CLI を使用する。GitHub MCP の `create_pull_request` は 404 エラーが発生する場合があるため、`gh pr create` を推奨する。

```bash
# origin/main とのコンフリクトがある場合はリベースで解消
git fetch origin
git rebase origin/main
# コンフリクトがあれば手動解消 → git rebase --continue
# リベース後は force push が必要
git push --force-with-lease origin feature/{feature-name}

# PR を作成
gh pr create \
  --base main \
  --head feature/{feature-name} \
  --title "feat({feature-name}): {short description}" \
  --body "$(cat <<'EOF'
## Summary
- {変更内容のサマリー（3-5 bullet points）}

## Test plan
- [ ] {テスト項目}

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

PR のタイトルとボディは、実装内容に応じて適切に記述する。

## Step 4: Return to Original Branch

```bash
# /team-implement Step 0 で記録した元のブランチに戻る
git checkout {original-branch}
```

元のブランチ名が不明な場合はユーザーに確認する（通常は `main`）。

## Step 5: デプロイ情報を記録・投稿

### 5-1. [MUST] Linear タスクにデプロイ情報をコメント

**このサブステップは必須。スキップ不可。**

> **Linear タスクIDが無い場合**: ユーザーに「Linear タスクIDが見つかりません。IDを指定しますか？スキップしますか？」と確認する。暗黙的にスキップしてはならない。

git コマンドでブランチ・コミット情報を取得し、Linear タスクにコメントとして追加する：

```
手順 1: git コマンドで情報を取得
  git log main..HEAD --oneline          # コミット履歴
  git remote get-url origin             # リモートURL（GitHub URL構築用）
  git rev-parse HEAD                    # 最新コミットハッシュ

手順 2: Linear MCP ツールで、Linear タスクIDに以下をコメント:

## デプロイ完了: {feature}

### ブランチ
- [`feature/{feature-name}`]({branch URL on GitHub}) → origin に push 済み

### コミット履歴
- [{commit hash 1}]({commit URL 1}): {commit message 1}
- [{commit hash 2}]({commit URL 2}): {commit message 2}
...

### レビュー結果サマリー
- セキュリティ: {summary}
- コード品質: {summary}
- テストカバレッジ: {summary}

### PR
- [{PR title}]({PR URL})

### 次のステップ
- マージ待ち
```

> git コマンドで情報取得（`context: fork` で直接実行）、Linear MCP でコメント投稿。

### 5-2. [MUST] Linear タスクのステータスを "In Review" に変更

**このサブステップは必須。スキップ不可。**

> **Linear タスクIDが無い場合**: Step 5-1 と同様、ユーザーに確認する。

Linear コメント投稿後、タスクのステータスを "In Review" に変更する：

```
手順 1: list_issue_statuses でチームのステータス一覧を取得し、"In Review" の stateId を特定
手順 2: save_issue でタスクのステータスを "In Review" に更新
```

> Step 5-1 の Linear コメントと合わせて実行する。コメント → ステータス変更の順序で行う。

### 5-3. [MUST] タスクファイルを完了状態に更新 + Decision Log に POST エントリ追記

**このサブステップは必須。スキップ不可。**

タスクファイル `.claude/docs/decisions/task-{id}-{feature}.md` を更新:

1. frontmatter の `status: active` を `status: completed` に変更
2. `## Decision Log` セクションに POST エントリを追記:

```markdown
### [deploy] POST — {date}

- **担当者**: Claude Lead
- **概要**: フィーチャーブランチを origin に push、PR 作成、{original_branch} に復帰
- **成果物**: ブランチ `feature/{feature-name}` on origin、PR {PR_URL}

### デプロイ詳細
- ブランチ: `feature/{feature-name}` → origin
- コミット数: {commit_count}件
- PR: {PR_URL}
- レビュー状況: Critical/High 発見事項は解決済み
- Linear: コメント投稿済み、ステータス "In Review" に変更済み
```

---

## Completion Report

```markdown
## デプロイ完了: {feature}

- ブランチ: `feature/{feature-name}` → origin に push 済み
- PR: {PR URL}
- 現在のブランチ: `{original-branch}` に戻りました
- Linear: コメント追加済み、ステータス "In Review" に変更済み

### 次のステップ
- PR をレビュー・マージしてください
```

---

## Tips

- すべての git 操作は直接実行される（`context: fork` により分離されたコンテキストで実行）
- **PR 作成は `gh` CLI を使用する**（GitHub MCP の `create_pull_request` は不安定なため）
- push 前に必ず品質チェックを確認する
- origin/main とのコンフリクトがある場合はリベースで解消してから PR を作成する
- 元のブランチに戻れない場合は `git checkout main` にフォールバック
- **Ad-hoc Git モード**: ユーザーの要求に応じて任意の git コマンドを実行できる。Linear 投稿等は不要
- **モード判定**: PR作成 + push が明示されていれば Deploy Workflow、それ以外は Ad-hoc Git
