# Claude Code Orchestra

**マルチエージェント協調フレームワーク（Opus 4.6 + Agent Teams 対応）**

Claude Code が OpenCode CLI（深い推論）と Gemini CLI（外部情報・マルチモーダル）を統合し、Agent Teams で並列開発を加速する。

---

## Why This Exists

| Agent | Strength | Use For |
|-------|----------|---------|
| **Claude Code** | オーケストレーション、Agent Teams | 全体統括、ユーザー対話、並列チーム管理 |
| **OpenCode CLI** | 深い推論、設計判断、デバッグ | 設計相談、エラー分析、トレードオフ評価 |
| **Gemini CLI** | Google Search、マルチモーダル、コードベース分析 | 外部情報取得、ライブラリ調査、コードベース分析、PDF/動画/音声処理 |


---

## Adaptive Execution (MUST FOLLOW)

**タスクサイズに応じてリソース配分を最小化する。不要なエージェントは起動しない。**

| Tier | /startproject | /team-implement | /team-review | Gemini | OpenCode |
|------|-------------|----------------|-------------|--------|-------|
| **XS** | 不要 | Claude 直接 | スキップ | 不要 | 不要 |
| **S** | Phase 1 のみ | Claude 直接 | Claude 直接 | 不要 | 不要 |
| **M** | Phase 1 + OpenCode サブエージェント | Claude or 小チーム | 2 レビュアー | 必要時のみ | サブエージェント |
| **L** | フル Agent Teams | フルチーム | 4 レビュアー | 標準 | Agent Teams |

分類ロジック: `tier = max(file_tier, complexity_tier, risk_tier)`

→ 詳細: `.claude/rules/adaptive-execution.md`

---

## Tool Routing (MUST FOLLOW)

**以下のルーティングルールは必ず遵守すること。Claude が直接実行してはならない操作が定義されている。**

**違反した場合、PreToolUse hook (`enforce-tool-routing.py`) が警告を発する。**

### 直接実行を禁止する操作

| 操作カテゴリ | コマンド例 | ルーティング先 |
|-------------|-----------|---------------|
| **Git 操作** | `git commit/push/pull/merge/rebase/checkout/branch/log/diff` | **MUST** → Gemini サブエージェント経由 |
| **Git 履歴探索** | `git blame/show/bisect/reflog/shortlog` | **MUST** → Gemini サブエージェント経由 |
| **Docker** | `docker build/run`, `docker-compose up` | **MUST** → Gemini サブエージェント経由 |
| **Lint/Format** | `ruff check`, `ruff format` | **MUST** → Gemini サブエージェント経由 |
| **依存管理** | `uv add/remove/sync/lock` | **MUST** → Gemini サブエージェント経由 |
| **GitHub MCP** | PR 作成、Issue 操作 | **MUST** → Gemini が計画、Claude MCP で実行 |
| **Linear MCP** | Issue 作成・更新 | **MUST** → Gemini が計画、Claude MCP で実行 |
| **コードベース分析** | アーキテクチャ分析、横断的依存関係調査 | **MUST** → Gemini サブエージェント経由（`gemini-explore` 推奨） |

### 例外（Claude が直接実行してよい操作）

- `git status`（現在の状態確認のみ）
- `git branch --show-current`（現在のブランチ名取得）
- `git rev-parse`, `git config --get`（情報取得）
- `.gitignore` 等の設定ファイル読み取り（Read ツール経由）
- 特定ファイルの読み取り・特定シンボルの検索（Read / Grep / Glob ツール経由）

### ルーティング方法

```
Task tool:
  subagent_type: "general-purpose"
  prompt: |
    {task description}
    gemini -p "Plan: {task}" 2>/dev/null
    Then execute the commands based on Gemini's plan.
```

→ 詳細: `.claude/rules/tool-routing.md`

---

## Context Management

Claude Code (Opus 4.6) のコンテキストは **1M トークン**（実質 **350-500k**、ツール定義等で縮小）。

**Compaction 機能**により、長時間セッションでもサーバーサイドで自動要約される。

### OpenCode/Gemini 呼び出し基準

| 出力サイズ | 方法 | 理由 |
|-----------|------|------|
| 短い（〜50行） | 直接呼び出しOK | 1Mコンテキストで十分吸収可能 |
| 大きい（50行以上） | サブエージェント経由を推奨 | コンテキスト効率化 |
| 分析レポート | サブエージェント → ファイル保存 | 詳細は `.claude/docs/` に永続化 |

### 並列処理の選択

| 目的 | 方法 | 適用場面 |
|------|------|----------|
| 結果を取得するだけ | サブエージェント | OpenCode設計相談、Gemini調査 |
| 相互通信が必要 | **Agent Teams** | Research↔Design、並列実装、並列レビュー |

---

## Quick Reference

### OpenCode を使う時

- 設計判断（「どう実装？」「どのパターン？」）
- デバッグ（「なぜ動かない？」「エラーの原因は？」）
- 比較検討（「AとBどちらがいい？」）

→ 詳細: `.claude/rules/opencode-delegation.md`

### Gemini を使う時

- コードベース分析（「コードベースを理解して」「アーキテクチャを分析して」）
- 外部リサーチ（「最新のドキュメントは？」「ライブラリを調べて」）
- マルチモーダル（「このPDF/動画/音声を見て」）

→ 詳細: `.claude/rules/gemini-delegation.md`

---

## Workflow

```
/startproject <機能名>     Step 0: サイズ判定 → Phase 1-3（tier に応じて適応）
    ↓ 承認後
/team-implement            Claude 直接 or Agent Teams（tier に応じて適応）
    ↓ 完了後
/team-review               Claude 直接 or 並列レビュー（tier に応じて適応）
```

1. Claude がタスクサイズを判定（XS/S/M/L）→ ワークフローを適応
2. Claude がユーザーと要件ヒアリング、コードベースを直接分析
3. **M**: OpenCode サブエージェントで設計 / **L**: Agent Teams で調査・設計
4. 承認後、`/team-implement` で実装（tier に応じた規模）
5. `/team-review` でレビュー（tier に応じた規模）

→ 詳細: `/startproject`, `/team-implement`, `/team-review` skills

---

## Tech Stack

- **Python** / **uv** (pip禁止)
- **ruff** (lint/format) / **ty** (type check) / **pytest**
- `poe lint` / `poe test` / `poe all`

→ 詳細: `.claude/rules/dev-environment.md`

---

## Documentation

| Location | Content |
|----------|---------|
| `.claude/rules/` | コーディング・セキュリティ・言語ルール |
| `.claude/docs/DESIGN.md` | 設計決定の記録 |
| `.claude/docs/research/` | 調査結果（Gemini / レビュー） |
| `.claude/docs/libraries/` | ライブラリ制約ドキュメント |
| `.claude/logs/cli-tools.jsonl` | OpenCode/Gemini入出力ログ |

---

## Language Protocol

- **思考・コード**: 英語
- **ユーザー対話**: 日本語
