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

**Gemini の役割は「外部リサーチ」と「マルチモーダル処理」に限定される。**

**`context: fork` スキル内では、git/ruff/uv 等のコマンドを直接実行できる。**

### Gemini を使う操作（リサーチ・マルチモーダルのみ）

| 操作カテゴリ | ルーティング先 |
|-------------|---------------|
| **外部リサーチ** | Gemini サブエージェント（Google Search grounding） |
| **マルチモーダル** | Gemini サブエージェント（PDF/動画/音声） |
| **ライブラリ調査** | Gemini サブエージェント |
| **コードベース分析** | Gemini サブエージェント（`gemini-explore` 推奨） |
| **設計判断** | OpenCode サブエージェント |

### `context: fork` スキルでの直接実行

以下のスキルは `context: fork` で実行され、メインのルーティングフックを経由しないため、git/ruff/uv 等を直接実行する：

| スキル | 直接実行する操作 |
|--------|----------------|
| `/team-implement` | git checkout/branch、ruff、pytest、uv |
| `/team-review` | git diff/log、pytest |
| `/deploy` | git push、gh pr create、git checkout |

### アドホック操作のルーティング

スキル外でのアドホックな操作は、PreToolUse hook (`enforce-tool-routing.py`) によりサブエージェント経由が推奨される：

- `git status`, `git branch --show-current`, `git rev-parse`, `git config --get` → Claude が直接実行OK
- `.gitignore` 等の設定ファイル読み取り → Read ツール経由で直接OK
- 特定ファイルの読み取り・特定シンボルの検索 → Read / Grep / Glob ツール経由で直接OK
- その他の git/docker/ruff/uv 操作 → サブエージェント経由

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
    ↓ レビュー完了後（自動修正ループ含む）
/deploy                    PR 作成 + push
```

1. Claude がタスクサイズを判定（XS/S/M/L）→ ワークフローを適応
2. Claude がユーザーと要件ヒアリング、コードベースを直接分析
3. **M**: OpenCode サブエージェントで設計 / **L**: Agent Teams で調査・設計
4. 承認後、`/team-implement` で実装（tier に応じた規模）
5. `/team-review` でレビュー（tier に応じた規模、Medium+ は自動修正ループ）
6. `/deploy` で PR 作成・push（自動発火）

→ 詳細: `/startproject`, `/team-implement`, `/team-review` skills

### Skill Auto-Routing (MUST FOLLOW)

**スキル名を明示しなくても、ユーザーの意図に応じて自動的にスキルが提案される。**

`UserPromptSubmit` hook (`agent-router.py`) がプロンプトを分析し、4つのスキルのいずれかを `additionalContext` で提案する。

| ユーザーの意図 | 提案されるスキル | 例 |
|--------------|----------------|-----|
| 新機能・プロジェクト開始 | `/startproject` | 「新機能を作りたい」「issueを進めたい」 |
| 承認済み計画の実装 | `/team-implement` | 「この計画で実装して」「実装を開始」 |
| 実装済みコードのレビュー | `/team-review` | 「レビューして」「品質チェック」 |
| PR作成・push | `/deploy` | 「PRを作って」「デプロイして」 |

**自動ルーティングが発火しないケース（例外的な処理）:**
- 質問・説明依頼（「これは何？」「なぜ失敗した？」）
- 単発の軽微な操作（「コミットして」「修正して」「フォーマットして」）
- 短いプロンプト（5文字未満）
- 既にスキル名が明示されている場合

→ 詳細: `.claude/hooks/agent-router.py`

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
| `.claude/docs/decisions/task-{id}-{feature}.md` | 統合タスクファイル（Brief + Implementation + Fix Tasks + Decision Log） |
| `.claude/docs/research/` | 調査結果（Gemini / レビュー） |
| `.claude/docs/libraries/` | ライブラリ制約ドキュメント |
| `.claude/logs/cli-tools.jsonl` | OpenCode/Gemini入出力ログ |

---

## Language Protocol

- **思考・コード**: 英語
- **ユーザー対話**: 日本語
