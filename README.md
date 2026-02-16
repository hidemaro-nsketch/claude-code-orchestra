# claude-code-orchestra

![Claude Code Orchestra](./summary.png)

Multi-Agent AI Development Environment

```
Claude Code (Orchestrator) ─┬─ Codex CLI (Deep Reasoning)
                            ├─ Gemini CLI (Research)
                            └─ Subagents (Parallel Tasks)
```

## Quick Start

既存プロジェクトのルートで実行:

```bash
git clone --depth 1 https://github.com/DeL-TaiseiOzaki/claude-code-orchestra.git .starter && cp -r .starter/.claude .starter/.codex .starter/.gemini .starter/CLAUDE.md . && rm -rf .starter && claude
```

## Prerequisites

### Claude Code

```bash
npm install -g @anthropic-ai/claude-code
claude login
```

### Codex CLI

```bash
npm install -g @openai/codex
codex login
```

### Gemini CLI

```bash
npm install -g @google/gemini-cli
gemini login
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           Claude Code (Orchestrator)                        │
│           → コンテキスト節約が最優先                         │
│           → ユーザー対話・調整・実行を担当                   │
│                      ↓                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Subagent (general-purpose)               │  │
│  │              → 独立したコンテキストを持つ               │  │
│  │              → Codex/Gemini を呼び出し可能             │  │
│  │              → 結果を要約してメインに返す              │  │
│  │                                                       │  │
│  │   ┌──────────────┐        ┌──────────────┐           │  │
│  │   │  Codex CLI   │        │  Gemini CLI  │           │  │
│  │   │  設計・推論  │        │  リサーチ    │           │  │
│  │   │  デバッグ    │        │  マルチモーダル│          │  │
│  │   └──────────────┘        └──────────────┘           │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### コンテキスト管理（重要）

メインオーケストレーターのコンテキストを節約するため、大きな出力が予想されるタスクはサブエージェント経由で実行します。

| 状況 | 推奨方法 |
|------|----------|
| 大きな出力が予想される | サブエージェント経由 |
| 短い質問・短い回答 | 直接呼び出しOK |
| Codex/Gemini相談 | サブエージェント経由 |
| 詳細な分析が必要 | サブエージェント経由 → ファイル保存 |

## Directory Structure

```
.
├── CLAUDE.md                    # メインシステムドキュメント
├── README.md
├── pyproject.toml               # Python プロジェクト設定
├── uv.lock                      # 依存関係ロックファイル
│
├── .claude/
│   ├── agents/
│   │   ├── general-purpose.md   # 汎用サブエージェント
│   │   ├── codex-debugger.md    # エラー分析エージェント
│   │   └── gemini-explore.md    # コードベース探索エージェント
│   │
│   ├── skills/                  # 再利用可能なワークフロー
│   │   ├── startproject/        # プロジェクト開始
│   │   ├── plan/                # 実装計画作成
│   │   ├── tdd/                 # テスト駆動開発
│   │   ├── checkpointing/       # セッション永続化
│   │   ├── codex-system/        # Codex CLI連携
│   │   ├── gemini-system/       # Gemini CLI連携
│   │   └── ...
│   │
│   ├── hooks/                   # 自動化フック
│   │   ├── agent-router.py      # エージェントルーティング
│   │   ├── lint-on-save.py      # 保存時自動lint
│   │   └── ...
│   │
│   ├── rules/                   # 開発ガイドライン
│   │   ├── coding-principles.md
│   │   ├── testing.md
│   │   └── ...
│   │
│   ├── docs/
│   │   ├── DESIGN.md            # 設計決定記録
│   │   ├── research/            # Gemini調査結果
│   │   └── libraries/           # ライブラリ制約
│   │
│   └── logs/
│       └── cli-tools.jsonl      # Codex/Gemini入出力ログ
│
├── .codex/                      # Codex CLI設定
│   ├── AGENTS.md
│   └── config.toml
│
└── .gemini/                     # Gemini CLI設定
    ├── GEMINI.md
    └── settings.json
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

## Skills

### `/startproject` — プロジェクト開始

マルチエージェント協調でプロジェクトを開始します。

```
/startproject ユーザー認証機能
```

**ワークフロー:**
1. **Gemini** → リポジトリ分析・事前調査
2. **Claude** → 要件ヒアリング・計画作成
3. **Codex** → 計画レビュー・リスク分析
4. **Claude** → タスクリスト作成

### `/plan` — 実装計画

要件を具体的なステップに分解します。

```
/plan APIエンドポイントの追加
```

**出力:**
- 実装ステップ（ファイル・変更内容・検証方法）
- 依存関係・リスク
- 検証基準

### `/tdd` — テスト駆動開発

Red-Green-Refactorサイクルで実装します。

```
/tdd ユーザー登録機能
```

**ワークフロー:**
1. テストケース設計
2. 失敗するテスト作成（Red）
3. 最小限の実装（Green）
4. リファクタリング（Refactor）

### `/checkpointing` — セッション永続化

セッションの状態を保存します。

```bash
/checkpointing              # 基本: 履歴ログ
/checkpointing --full       # 完全: git履歴・ファイル変更含む
/checkpointing --analyze    # 分析: 再利用可能なスキルパターン発見
```

### `/codex-system` — Codex CLI連携

設計判断・デバッグ・トレードオフ分析に使用します。

**トリガー例:**
- 「どう設計すべき？」「どう実装する？」
- 「なぜ動かない？」「エラーが出る」
- 「どちらがいい？」「比較して」

### `/gemini-system` — Gemini CLI連携

リサーチ・大規模分析・マルチモーダル処理に使用します。

**トリガー例:**
- 「調べて」「リサーチして」
- 「このPDF/動画を見て」
- 「コードベース全体を理解して」

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
  ├── Quality Reviewer    → コード品質・命名・パターン (Codex活用)
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

feature ブランチを push し、元のブランチに戻ります。

```
/deploy
```

**ワークフロー:**
1. **品質チェック確認** → ruff / pytest の最終確認
2. **git push** → `feature/{name}` を origin に push
3. **ブランチ復帰** → 元のブランチに checkout
4. **Linear コメント** → ブランチURL・コミット履歴・レビューサマリーを投稿

### `/simplify` — コードリファクタリング

コードを簡潔化・可読性向上させます。

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
| `agent-router.py` | ユーザー入力 | Codex/Geminiへのルーティング提案 |
| `lint-on-save.py` | ファイル保存 | 自動lint実行 |
| `check-codex-before-write.py` | ファイル書き込み前 | Codex相談提案 |
| `log-cli-tools.py` | Codex/Gemini実行 | 入出力ログ記録 |

## Language Rules

- **コード・思考・推論**: 英語
- **ユーザーへの応答**: 日本語
- **技術ドキュメント**: 英語
- **README等**: 日本語可
