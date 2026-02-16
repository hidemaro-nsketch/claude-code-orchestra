---
name: deploy
description: |
  Push the feature branch to remote and switch back to the original branch.
  Run after /team-review completes. Handles git push and branch cleanup.
metadata:
  short-description: Push feature branch and return to original branch
---

# Deploy

**feature ブランチを push し、元のブランチに戻る。**

## Prerequisites

- `/team-implement` で feature ブランチが作成されていること
- `/team-review` が完了していること
- すべての品質チェックがパスしていること

## Workflow

```
Step 1: 品質チェック確認
  ↓
Step 2: feature ブランチを push
  ↓
Step 3: 元のブランチに戻る
  ↓
Step 4: Linear タスクにデプロイ情報をコメント
```

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

## Step 3: Return to Original Branch

```bash
# /team-implement Step 0 で記録した元のブランチに戻る
git checkout {original-branch}
```

元のブランチ名が不明な場合はユーザーに確認する（通常は `main`）。

## Step 4: Post Deploy Info to Linear

GitHub MCP でブランチ・コミット情報を取得し、Linear タスクにコメントとして追加する：

```
Step 1: GitHub MCP ツールで情報を取得
  - feature/{feature-name} ブランチの詳細（URL、保護状態）
  - コミット履歴（ハッシュ、メッセージ、URL）
  - push 先の確認

Step 2: Linear MCP ツールで、Linear タスクIDに以下をコメント:

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

### 次のステップ
- PR 作成 / マージ待ち
```

> **Routing**: `.claude/rules/tool-routing.md` に従い、GitHub MCP で情報取得、Linear MCP でコメント投稿。

### Step 4b: Save Deploy Record Locally

デプロイ情報をローカルログに記録する：

`.claude/docs/decisions/log-{feature}.md` に POST エントリを追記:

```markdown
### [deploy] POST — {date}

- **担当者**: Claude Lead（Gemini サブエージェント経由）
- **概要**: フィーチャーブランチを origin に push、{original_branch} に復帰
- **成果物**: ブランチ `feature/{feature-name}` on origin

### デプロイ詳細
- ブランチ: `feature/{feature-name}` → origin
- コミット数: {commit_count}件
- レビュー状況: Critical/High 発見事項は解決済み
- Linear: コメント投稿済み
```

---

## Completion Report

```markdown
## デプロイ完了: {feature}

- ブランチ: `feature/{feature-name}` → origin に push 済み
- 現在のブランチ: `{original-branch}` に戻りました
- Linear: コメント追加済み

### 次のステップ
- PR を作成してマージしてください
- 必要に応じて `gh pr create` を実行できます
```

---

## Tips

- すべての git 操作は Gemini サブエージェント経由で実行される
- push 前に必ず品質チェックを確認する
- 元のブランチに戻れない場合は `git checkout main` にフォールバック
