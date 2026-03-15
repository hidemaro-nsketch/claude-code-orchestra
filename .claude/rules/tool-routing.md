# Tool Routing Rules

**Defines which tools and operations are delegated to which agent.**

This file complements agent-specific rules (`opencode-delegation.md`, `gemini-delegation.md`)
by providing cross-cutting routing decisions.

## `context: fork` スキルの直接実行

以下のスキルは `context: fork` で実行され、メインのルーティングフックを経由しない。
スキル内では git/ruff/uv/gh 等を直接実行する（Gemini 経由不要）：

| スキル | 直接実行する操作 |
|--------|----------------|
| `/team-implement` | git checkout/branch、ruff、pytest、uv、Linear MCP |
| `/team-review` | git diff/log、pytest、ruff |
| `/deploy` | git push、gh pr create、git checkout、Linear MCP |

## Adaptive Execution Override

> 参照: `.claude/rules/adaptive-execution.md`

ルーティングルールはタスクサイズに応じて適応される：

- **XS/S タスク**: OpenCode/Gemini への委託は不要。Claude が直接対応する。
- **M タスク**: 必要な場合のみ OpenCode サブエージェントで設計相談。Gemini は未知のライブラリ・外部 API がある場合のみ。
- **L タスク**: フルルーティング（全ルール適用）。

## Routing Table

| Operation | Delegate To | Method |
|-----------|-------------|--------|
| External research | **Gemini** | Subagent or Agent Teams |
| Multimodal (PDF/video/audio) | **Gemini** | Subagent |
| Codebase analysis | **Gemini subagent** | `gemini-explore` or `general-purpose` |
| Library research | **Gemini** | Google Search grounding |
| Design decisions | **OpenCode** | Subagent or Agent Teams |
| git/docker/ruff/uv (in `context: fork` skills) | **Direct** | スキル内で直接実行 |
| git/docker/ruff/uv (ad-hoc) | **Subagent** | サブエージェント経由で直接実行 |
| GitHub MCP / Linear MCP | **Direct or Subagent** | スキル内は直接、アドホックはサブエージェント |

## Codebase Analysis via Gemini

Codebase analysis should be routed through a Gemini subagent (preferably `gemini-explore`).

### Scope

- Repository-wide architecture analysis
- Cross-module dependency understanding
- Pattern discovery across the codebase
- Data flow and impact analysis
- Code structure overview

### How to Route

```
Task tool parameters:
- subagent_type: "gemini-explore"  (preferred)
- run_in_background: true
- prompt: |
    Analyze the codebase: {description}

    Use Gemini CLI with --include-directories to analyze:
    gemini -p "{analysis question}" --include-directories . 2>/dev/null

    Follow up with local tools (Grep/Read/Glob) for targeted inspection.

    Save full output to: .claude/docs/research/{topic}.md
    Return CONCISE summary.
```

### Triggers

| User Input | Action |
|------------|--------|
| 「コードベースを理解して」「アーキテクチャ分析して」 | Route to Gemini subagent |
| 「コード全体を見て」「横断的に分析して」 | Route to Gemini subagent |
| 「依存関係を調べて」「影響範囲を分析して」 | Route to Gemini subagent |

### Exceptions (Claude handles directly)

- Reading a specific single file (Read tool)
- Searching for a specific symbol/function (Grep/Glob tools)
- Quick reference during implementation (targeted file reads)

## Git Operations

### `context: fork` スキル内

`/team-implement`, `/team-review`, `/deploy` はスキル内で git コマンドを直接実行する。

### アドホック操作

スキル外でのアドホックな git 操作はサブエージェント経由で実行する（コンテキスト分離のため）。

#### Claude が直接実行してよい操作

- `git status`（現在の状態確認のみ）
- `git branch --show-current`（現在のブランチ名取得）
- `git rev-parse`, `git config --get`（情報取得）
- `.gitignore` 等の設定ファイル読み取り（Read ツール経由）

#### サブエージェント経由で実行する操作

```
Task tool parameters:
- subagent_type: "general-purpose"
- prompt: |
    Perform the following git operation.
    Task: {description}
    Execute the git commands directly and report results concisely.
```

### Git Triggers

| User Input | Action |
|------------|--------|
| 「コミットして」「pushして」 | サブエージェント経由で実行 |
| 「PRを作って」「ブランチを切って」 | サブエージェント経由で実行 |
| 「git log見せて」「差分を見せて」 | サブエージェント経由で実行 |
| 「履歴を調べて」「blame して」 | サブエージェント経由で実行 |

## GitHub / Linear MCP Operations

### `context: fork` スキル内

`/team-implement` と `/deploy` はスキル内で git コマンドによる情報取得 + Linear MCP を直接実行する。

### アドホック操作

スキル外での MCP 操作はサブエージェント経由で実行する。

```
Task tool parameters:
- subagent_type: "general-purpose"
- prompt: |
    Perform the following MCP operation.
    Task: {description}
    Use Linear/GitHub MCP tools directly.
    Report results back concisely in Japanese.
```

### Linear Triggers

| User Input | Action |
|------------|--------|
| 「Linearにissue作って」 | サブエージェント経由で実行 |
| 「チケットを更新して」 | サブエージェント経由で実行 |
| 「タスクのステータスを変えて」 | サブエージェント経由で実行 |

## Operational Commands (Subagent Routing)

以下の操作はアドホック実行時にサブエージェント経由で実行する（コンテキスト分離のため）。
`context: fork` スキル内では直接実行される。

### 共通ルーティング方法

```
Task tool parameters:
- subagent_type: "general-purpose"
- prompt: |
    Task: {description}
    Execute the commands directly and report results concisely.
```

### 対象操作と Triggers

| 操作 | コマンド例 | Triggers |
|------|-----------|----------|
| **依存管理** | `uv add/remove/sync` | 「パッケージを更新して」「依存を追加して」 |
| **Lint/Format** | `ruff check .`, `ruff format .` | 「lintして」「フォーマットして」 |
| **Docker** | `docker build/run`, `docker compose` | 「コンテナを起動して」「docker build して」 |
| **環境セットアップ** | `uv sync`, version checks | 「環境セットアップして」「バージョン確認して」 |
| **ファイル整理** | bulk rename, directory restructure | 「ファイルを整理して」「リネームして」 |
| **シェルスクリプト** | Bash script creation | 「スクリプト書いて」「自動化して」 |
| **Changelog** | `git log` → formatted notes | 「changelog作って」「リリースノート生成して」 |

### 例外（Claude が直接実行してよい操作）

- ファイル内容の編集（Edit/Write ツール）
- 新規ソースコード作成（Claude の領域）

### Gemini を使うケース（外部情報が必要な場合のみ）

以下の場合はサブエージェント内で Gemini CLI を併用する：

- パッケージの最新バージョン・脆弱性チェック（Google Search grounding）
- 未知のライブラリの使い方調査

```
gemini -p "Check the latest stable versions and known issues for: {packages}" 2>/dev/null
```

---

## Adding New Routes

To add a new tool routing rule:

1. Add entry to the **Routing Table** above
2. Define **Scope** (what operations are covered)
3. Define **How to Route** (subagent prompt template)
4. Define **Trigger Detection** (user input patterns)
5. Note any **Exceptions** (when Claude handles directly)
