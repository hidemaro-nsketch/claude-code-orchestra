# claude-code-orchestra

Multi-Agent AI Development Environment

```
Claude Code (Orchestrator) ─┬─ OpenCode CLI (Deep Reasoning)
                            ├─ Gemini CLI (Research)
                            └─ Subagents (Parallel Tasks)
```

forked from https://github.com/DeL-TaiseiOzaki/claude-code-orchestra


## Quick Start

## Prerequisites

### Claude Code

```bash
npm install -g @anthropic-ai/claude-code
claude login
```

### OpenCode CLI

```bash
npm install -g @anthropic-ai/opencode
opencode login
```

### Gemini CLI

```bash
npm install -g @google/gemini-cli
gemini login
```

## Workflow

```
/startproject <機能名>     計画: 理解 → 調査&設計 → ユーザー承認
    ↓ 承認後
/team-implement            実装: Agent Teams で並列実装
    ↓ 完了後
/team-review               レビュー: 4専門レビュアー並列 → simplify
    ↓ 完了後
/deploy                    デプロイ: push → Linear更新
```


## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│           Claude Code (Orchestrator / 1M Context)            │
│           → ユーザー対話・調整・実行を担当                    │
│           → コードベース分析は Gemini サブエージェントに委託   │
│           → Agent Teams で並列開発を管理                      │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                   Agent Teams                          │  │
│  │  /startproject   → Researcher + Architect 並列          │  │
│  │  /team-implement → Implementer + Tester 並列           │  │
│  │  /team-review    → Security + Quality + Test + Simplify │  │
│  │  /deploy         → push + Linear更新                    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Subagent (general-purpose)                 │  │
│  │              → Tool Routing: git/lint/docker 等を委託   │  │
│  │              → OpenCode/Gemini を呼び出し可能            │  │
│  │              → 結果を要約してメインに返す               │  │
│  │                                                        │  │
│  │   ┌──────────────┐        ┌──────────────┐            │  │
│  │   │ OpenCode CLI │        │  Gemini CLI  │            │  │
│  │   │  設計・推論  │        │  リサーチ    │            │  │
│  │   │  デバッグ    │        │  マルチモーダル│           │  │
│  │   └──────────────┘        └──────────────┘            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              MCP Integrations                          │  │
│  │              → GitHub MCP (PR・Issue・コミット)         │  │
│  │              → Linear MCP (タスク管理)                  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Tool Routing

Git / Docker / Lint 等の操作は Claude が直接実行せず、Gemini サブエージェント経由で実行する。

| 操作 | ルーティング先 |
|------|---------------|
| git commit/push/merge 等 | Gemini サブエージェント |
| ruff check/format | Gemini サブエージェント |
| uv add/sync | Gemini サブエージェント |
| docker build/run | Gemini サブエージェント |
| GitHub/Linear MCP | Gemini が計画 → Claude MCP で実行 |
| コードベース分析 | Gemini サブエージェント |
| 設計判断 | OpenCode |
| 外部リサーチ | Gemini |

→ 詳細: `.claude/rules/tool-routing.md`

## Directory Structure

```
.
├── CLAUDE.md                    # メインシステムドキュメント
├── README.md
├── pyproject.toml               # Python プロジェクト設定
├── uv.lock                      # 依存関係ロックファイル
├── scripts/                     # ユーティリティスクリプト
│
├── .claude/
│   ├── settings.json            # Claude Code 設定
│   ├── settings.local.json      # ローカル設定（gitignore）
│   │
│   ├── agents/                  # カスタムエージェント定義
│   │   ├── general-purpose.md   # 汎用サブエージェント
│   │   ├── opencode-debugger.md  # エラー分析エージェント
│   │   └── gemini-explore.md    # コードベース探索エージェント
│   │
│   ├── skills/                  # 再利用可能なワークフロー
│   │   ├── startproject/        # プロジェクト開始（Agent Teams）
│   │   ├── team-implement/      # 並列実装（Agent Teams）
│   │   ├── team-review/         # 並列レビュー（Agent Teams）
│   │   ├── deploy/              # デプロイ（push + Linear更新）
│   │   ├── plan/                # 実装計画作成
│   │   ├── tdd/                 # テスト駆動開発
│   │   ├── checkpointing/       # セッション永続化
│   │   ├── opencode-system/     # OpenCode CLI連携
│   │   ├── gemini-system/       # Gemini CLI連携
│   │   ├── simplify/            # コードリファクタリング
│   │   ├── design-tracker/      # 設計決定追跡
│   │   ├── research-lib/        # ライブラリ調査
│   │   ├── update-design/       # 設計ドキュメント更新
│   │   └── update-lib-docs/     # ライブラリドキュメント更新
│   │
│   ├── hooks/                   # 自動化フック
│   │   ├── enforce-tool-routing.py  # ツールルーティング強制
│   │   ├── agent-router.py          # エージェントルーティング提案
│   │   ├── lint-on-save.py          # 保存時自動lint
│   │   ├── check-opencode-before-write.py  # 書き込み前OpenCode相談
│   │   ├── check-opencode-after-plan.py    # 計画後OpenCode相談
│   │   ├── error-to-opencode.py        # エラー時OpenCode分析
│   │   ├── post-implementation-review.py  # 実装後レビュー
│   │   ├── post-test-analysis.py    # テスト後分析
│   │   ├── suggest-gemini-research.py   # Geminiリサーチ提案
│   │   └── log-cli-tools.py         # CLI入出力ログ記録
│   │
│   ├── rules/                   # 開発ガイドライン
│   │   ├── tool-routing.md      # ツールルーティングルール
│   │   ├── opencode-delegation.md  # OpenCode委託ルール
│   │   ├── gemini-delegation.md # Gemini委託ルール
│   │   ├── coding-principles.md # コーディング原則
│   │   ├── dev-environment.md   # 開発環境
│   │   ├── testing.md           # テストガイドライン
│   │   ├── security.md          # セキュリティルール
│   │   └── language.md          # 言語ルール
│   │
│   ├── docs/
│   │   ├── DESIGN.md            # 設計決定記録
│   │   ├── research/            # 調査結果・レビューレポート
│   │   └── libraries/           # ライブラリ制約
│   │
│   └── logs/
│       └── cli-tools.jsonl      # OpenCode/Gemini入出力ログ
│
├── .opencode/                   # OpenCode CLI設定
│   ├── AGENTS.md
│   ├── config.toml
│   └── skills/
│       └── context-loader/      # コンテキストローダー
│
└── .gemini/                     # Gemini CLI設定
    ├── GEMINI.md
    ├── settings.json
    └── skills/
        └── context-loader/      # コンテキストローダー
```


## Skills

### `/startproject` — プロジェクト開始

マルチエージェント協調でプロジェクトを開始します。

```
/startproject ユーザー認証機能
```

**ワークフロー:**
1. **Gemini** → リポジトリ分析・事前調査
2. **Claude** → 要件ヒアリング・計画作成
3. **OpenCode** → 計画レビュー・リスク分析
4. **Claude** → タスクリスト作成


### `/team-implement` — 並列実装

Agent Teams でモジュール単位の並列実装を行います。

```
/team-implement
```

**ワークフロー:**
1. **計画分析** → タスク依存関係からチーム構成を決定
2. **feature ブランチ作成** → `feature/{name}` で作業開始
3. **Agent Teams 起動** → モジュール別 Implementer + Tester を並列起動
4. **モニタリング** → Lead が進捗管理・競合解決
5. **統合検証** → ruff / ty / pytest で品質チェック
6. **Linear コメント** → コミット履歴・品質結果を投稿

### `/team-review` — 並列レビュー

Agent Teams で4つの専門視点から同時にレビューします。

```
/team-review
```

**ワークフロー:**

```
Step 1: Gather Diff
  git diff main...HEAD で変更範囲を特定
    ↓
Step 2: Spawn Review Team (4人並列)
  ├── Security Reviewer   → 脆弱性・認証・入力検証
  ├── Quality Reviewer    → コード品質・命名・パターン (OpenCode活用)
  ├── Test Reviewer       → カバレッジ・テスト品質
  └── Simplify Reviewer   → 構造的複雑性・リファクタリング候補
    ↓
Step 3: Synthesize Findings
  4つのレポートを統合、優先度付け (Critical > High > Medium > Low)
    ↓
Step 4: Report to User
  統合結果 + simplify 対象リストを提示
    ↓ ユーザー承認
Step 5: Simplify (Optional)
  承認された箇所のリファクタリング実行 + テスト確認
```

**レビューレポート出力先:**

| レビュアー | 出力ファイル |
|-----------|-------------|
| Security | `.claude/docs/research/review-security-{feature}.md` |
| Quality | `.claude/docs/research/review-quality-{feature}.md` |
| Test | `.claude/docs/research/review-tests-{feature}.md` |
| Simplify | `.claude/docs/research/review-simplify-{feature}.md` |

### `/deploy` — デプロイ

feature ブランチを push し、PR を作成して、元のブランチに戻ります。

```
/deploy
```

**ワークフロー:**
1. **品質チェック確認** → ruff / pytest の最終確認
2. **git push** → `feature/{name}` を origin に push
3. **PR 作成** → `gh pr create` で Pull Request を作成
4. **ブランチ復帰** → 元のブランチに checkout
5. **Linear コメント** → ブランチURL・コミット履歴・PR リンク・レビューサマリーを投稿

### `/design-tracker` — 設計決定追跡

アーキテクチャ・実装決定を自動記録します。

## Development

### Tech Stack

| ツール | 用途 |
|--------|------|
| **uv** | パッケージ管理（pip禁止） |
| **ruff** | リント・フォーマット |
| **ty** | 型チェック |
| **pytest** | テスト |
| **poethepoet** | タスクランナー |

### Commands

```bash
# 依存関係
uv add <package>           # パッケージ追加
uv add --dev <package>     # 開発依存追加
uv sync                    # 依存関係同期

# 品質チェック
poe lint                   # ruff check + format
poe typecheck              # ty
poe test                   # pytest
poe all                    # 全チェック実行

# 直接実行
uv run pytest -v
uv run ruff check .
```

## Hooks

自動化フックにより、適切なタイミングでエージェント連携を提案します。

| フック | トリガー | 動作 |
|--------|----------|------|
| `agent-router.py` | ユーザー入力 | OpenCode/Geminiへのルーティング提案 |
| `lint-on-save.py` | ファイル保存 | 自動lint実行 |
| `check-opencode-before-write.py` | ファイル書き込み前 | OpenCode相談提案 |
| `log-cli-tools.py` | OpenCode/Gemini実行 | 入出力ログ記録 |

## Language Rules

- **コード・思考・推論**: 英語
- **ユーザーへの応答**: 日本語
- **技術ドキュメント**: 英語
- **README等**: 日本語可


## Migration Tool

他のプロジェクトに Skills / Rules / Hooks を移植するための対話型 CLI ツール。

```bash
python scripts/migrate-skills.py
```

### フェーズ構成

スキルとルールは依存関係に基づいて6つのフェーズに分割されている。必要なフェーズだけを選択して移植できる。

| Phase | 名前 | 内容 | ファイル数 |
|-------|------|------|-----------|
| **0** | Foundation Rules | 基本ルール（言語・コーディング・テスト・セキュリティ）+ lint-on-save フック | 5 |
| **1** | Standalone Skills | 外部 CLI 不要のスキル（plan, tdd, simplify, design-tracker, update-design）| 5 |
| **2** | Documentation Skills | ライブラリ調査・ドキュメント管理スキル | 2 |
| **3** | External CLI Integration | OpenCode CLI + Gemini CLI 連携（スキル・ルール・フック・エージェント定義）| 20+ |
| **4** | Agent Teams | 並列ワークフロー（startproject, team-implement, team-review, deploy）| 5 |
| **5** | Session Management | チェックポイント・プロジェクト初期化 | 3 |

### 使い方

```bash
# 対話型モード（fzf でフェーズとターゲットを選択）
python scripts/migrate-skills.py

# プレビューのみ（ファイルを変更しない）
python scripts/migrate-skills.py --dry-run

# 非対話型（CI 等で使用）
python scripts/migrate-skills.py --phase 0,1,2 --target /path/to/project

# 既存ファイルを上書き
python scripts/migrate-skills.py --force
```

### 動作内容

- 選択したフェーズのファイルをターゲットにコピー
- `.claude/settings.json` にフック・パーミッション・環境変数をマージ
- `CLAUDE.md` にフェーズ対応のセクションを追加
- `.claude/.migrated-phases` に移植済みフェーズを記録（重複防止）

> fzf が必要（対話型モードの場合）。`--phase` / `--target` フラグで非対話型実行も可能。

## TODO

- routing 
https://github.com/musistudio/claude-code-router

- use playwrite mcp for web development (e.g. testing, e2e testing, web scraping)

- use git worktree for parallel development 

- use hook for slack notification

- use claude code mcp for mobile development (e.g. android, ios)

## reference 
- https://github.com/obra/superpowers
- https://github.com/zeroclaw-labs/zeroclaw
