# Skill Migration Plan

このリポジトリのスキル・ルールを既存リポジトリに段階的に移行するための実施計画。

---

## 全体方針

- **段階的移行**: 依存関係の少ないものから順に移行する
- **各フェーズで動作確認**: 移行したスキルが単独で動作することを確認してから次へ
- **ルールファイルはスキルとセット**: スキルが参照するルールファイルも同時に移行する
- **ディレクトリ構造を先に整備**: `.claude/` 配下の構造を最初に作る

---

## 前提: ディレクトリ構造の準備

全フェーズに先立ち、移行先リポジトリに以下の構造を作成する。

```
.claude/
├── rules/              # Phase 0 で作成
├── skills/             # Phase 1〜 で順次追加
├── docs/
│   ├── DESIGN.md       # Phase 1 で作成
│   ├── research/       # Phase 2 で作成
│   └── libraries/      # Phase 2 で作成
├── logs/               # Phase 5 で作成
└── checkpoints/        # Phase 5 で作成
```

---

## スキル一覧と依存関係マップ

| # | Skill | 外部CLI | Agent Teams | 依存ルール | 依存ディレクトリ | 移行Phase |
|---|-------|---------|-------------|-----------|-----------------|----------|
| 1 | plan | - | - | - | - | 1 |
| 2 | tdd | - | - | testing.md | - | 1 |
| 3 | simplify | - | - | coding-principles.md | `.claude/docs/libraries/` | 1 |
| 4 | design-tracker | - | - | - | `.claude/docs/DESIGN.md` | 1 |
| 5 | update-design | - | - | - | `.claude/docs/DESIGN.md` | 1 |
| 6 | research-lib | - | - | - | `.claude/docs/libraries/` | 2 |
| 7 | update-lib-docs | - | - | - | `.claude/docs/libraries/` | 2 |
| 8 | codex-system | Codex CLI | - | codex-delegation.md | `.claude/logs/` | 3 |
| 9 | gemini-system | Gemini CLI | - | gemini-delegation.md | `.claude/docs/research/` | 3 |
| 10 | startproject | Codex + Gemini | Required | 両方の delegation.md | 複数 | 4 |
| 11 | team-implement | - | Required | - | - | 4 |
| 12 | team-review | Codex CLI | Required | security.md, coding-principles.md, testing.md | `.claude/docs/research/` | 4 |
| 13 | checkpointing | - | - | - | `.claude/logs/`, `.claude/checkpoints/` | 5 |
| 14 | init | - | - | - | - | 5 |

---

## Phase 0: 基盤ルールの移行

**目的**: スキルが参照する共通ルールファイルを先に設置する。

### 対象ファイル

| ファイル | 内容 | 移行時の注意 |
|---------|------|-------------|
| `.claude/rules/language.md` | 言語ルール（日本語/英語の使い分け） | そのまま使えるが、プロジェクトに合わせて調整 |
| `.claude/rules/coding-principles.md` | コーディング原則 | そのまま使える |
| `.claude/rules/testing.md` | テストルール | テストフレームワークに合わせて調整 |
| `.claude/rules/security.md` | セキュリティルール | そのまま使える |
| `.claude/rules/codex-delegation.md` | Codex委譲ルール | Phase 3 で移行 |
| `.claude/rules/gemini-delegation.md` | Gemini委譲ルール | Phase 3 で移行 |

> **注**: `dev-environment.md` は移行しない。移行先リポジトリ固有のツールチェイン設定は各プロジェクトで個別に管理する。

### 作業手順

1. `.claude/rules/` ディレクトリを作成
2. `language.md`, `coding-principles.md`, `testing.md`, `security.md` をコピー
3. `CLAUDE.md` に rules への参照を追加（または既存のCLAUDE.mdにマージ）

### 確認項目

- [ ] Claude Code がルールを認識しているか（会話で確認）
- [ ] 移行先プロジェクトのツールチェインと矛盾がないか

---

## Phase 1: スタンドアロンスキル（外部依存なし）

**目的**: 外部CLIやAgent Teamsに依存しない、単独で動作するスキルを移行する。

### 1-1. plan

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/plan/SKILL.md` |
| 依存 | なし |
| 移行難易度 | 低 |
| 移行時の変更 | 不要（汎用的な計画作成ワークフロー） |

**作業**:
1. `.claude/skills/plan/SKILL.md` をコピー
2. 動作確認: `/plan <適当な機能>` を実行

### 1-2. tdd

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/tdd/SKILL.md` |
| 依存 | `.claude/rules/testing.md`（Phase 0 で移行済み） |
| 移行難易度 | 低 |
| 移行時の変更 | テストコマンド（`uv run pytest` → 移行先のテストコマンド）を確認 |

**作業**:
1. `.claude/skills/tdd/SKILL.md` をコピー
2. テストコマンド部分が移行先プロジェクトに合っているか確認
3. 動作確認: `/tdd <簡単な機能>` で Red-Green-Refactor サイクルを実行

### 1-3. simplify

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/simplify/SKILL.md` |
| 依存 | `.claude/rules/coding-principles.md`（Phase 0）、`.claude/docs/libraries/`（Phase 2 で本格利用） |
| 移行難易度 | 低 |
| 移行時の変更 | `.claude/docs/libraries/` が無くても動作する（制約チェックをスキップするだけ） |

**作業**:
1. `.claude/skills/simplify/SKILL.md` をコピー
2. 動作確認: `/simplify` で既存コードのリファクタリングを試行

### 1-4. design-tracker + update-design

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/design-tracker/SKILL.md`, `.claude/skills/update-design/SKILL.md` |
| 依存 | `.claude/docs/DESIGN.md` |
| 移行難易度 | 低 |
| 移行時の変更 | `DESIGN.md` のテンプレートを先に作成する必要あり |

**作業**:
1. `.claude/docs/DESIGN.md` のテンプレートを作成（空のセクション構造）
2. 両スキルのSKILL.mdをコピー
3. 動作確認: 設計議論をして `design-tracker` が自動発動するか確認
4. 動作確認: `/update-design` で手動更新を確認

**DESIGN.md テンプレート**:
```markdown
# Design Document

## Overview

## Architecture

## Implementation Plan

## TODO

## Open Questions

## Changelog
```

### Phase 1 完了チェックリスト

- [ ] `/plan` が動作する
- [ ] `/tdd` でテストが書ける
- [ ] `/simplify` でリファクタリングできる
- [ ] 設計議論で `design-tracker` が自動発動する
- [ ] `/update-design` で DESIGN.md が更新される

---

## Phase 2: ドキュメント基盤スキル

**目的**: ライブラリドキュメントの調査・管理スキルを移行する。

### 2-1. research-lib

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/research-lib/SKILL.md` |
| 依存 | `.claude/docs/libraries/` ディレクトリ |
| 移行難易度 | 低 |
| 移行時の変更 | 不要（WebSearch ツールを使用、外部CLIは不要） |

**作業**:
1. `.claude/docs/libraries/` ディレクトリを作成
2. `.claude/skills/research-lib/SKILL.md` をコピー
3. 動作確認: `/research-lib <使用中のライブラリ名>` を実行

### 2-2. update-lib-docs

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/update-lib-docs/SKILL.md` |
| 依存 | `.claude/docs/libraries/` に既存ドキュメントがあること |
| 移行難易度 | 低 |
| 移行時の変更 | 不要 |

**作業**:
1. `.claude/skills/update-lib-docs/SKILL.md` をコピー
2. 動作確認: Phase 2-1 で作成したドキュメントに対して `/update-lib-docs` を実行

### Phase 2 完了チェックリスト

- [ ] `/research-lib` でライブラリ調査ドキュメントが生成される
- [ ] `/update-lib-docs` で既存ドキュメントが更新される
- [ ] `.claude/docs/libraries/` にドキュメントが蓄積される

---

## Phase 3: 外部CLI連携スキル

**目的**: Codex CLI / Gemini CLI との連携スキルを移行する。

### 前提条件

- **Codex CLI** がインストール・認証済み
- **Gemini CLI** がインストール・認証済み

```bash
# インストール確認
codex --version
gemini --version

# 動作確認
codex exec --model gpt-5.3-codex --sandbox read-only --full-auto "Say hello" 2>/dev/null
gemini -p "Say hello" 2>/dev/null
```

### 3-1. codex-system

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/codex-system/SKILL.md` + `references/` 配下5ファイル |
| 依存 | Codex CLI、`.claude/rules/codex-delegation.md` |
| 移行難易度 | 中 |
| 移行時の変更 | ルールファイルのパスは変更不要（相対的に参照される） |

**作業**:
1. `.claude/rules/codex-delegation.md` をコピー
2. `.claude/skills/codex-system/` ディレクトリごとコピー（SKILL.md + references/）
3. `CLAUDE.md` に Codex 連携の記述を追加
4. 動作確認: 設計相談や「考えて」で Codex が呼ばれるか確認

### 3-2. gemini-system

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/gemini-system/SKILL.md` + `references/` 配下2ファイル |
| 依存 | Gemini CLI、`.claude/rules/gemini-delegation.md` |
| 移行難易度 | 中 |
| 移行時の変更 | コードベース分析をGeminiに委譲しないよう注意（SKILL.mdに既に記載済み） |

**作業**:
1. `.claude/rules/gemini-delegation.md` をコピー
2. `.claude/skills/gemini-system/` ディレクトリごとコピー（SKILL.md + references/）
3. `.claude/docs/research/` ディレクトリを作成
4. `CLAUDE.md` に Gemini 連携の記述を追加
5. 動作確認: 「調べて」「リサーチして」で Gemini が呼ばれるか確認

### Phase 3 完了チェックリスト

- [ ] Codex CLI / Gemini CLI がインストール・認証済み
- [ ] `/codex-system` で設計相談ができる
- [ ] 「考えて」「分析して」でプロアクティブに Codex が呼ばれる
- [ ] `/gemini-system` で外部リサーチができる
- [ ] 「調べて」「リサーチして」でプロアクティブに Gemini が呼ばれる
- [ ] 調査結果が `.claude/docs/research/` に保存される

---

## Phase 4: Agent Teams ワークフロー

**目的**: Agent Teams を使った並列ワークフロースキルを移行する。

### 前提条件

- Phase 3 が完了していること（Codex/Gemini が使える状態）
- Claude Code が Agent Teams 機能をサポートしていること（Opus 4.6）

### 4-1. startproject

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/startproject/SKILL.md` + `references/task-patterns.md` |
| 依存 | Codex CLI、Gemini CLI、Agent Teams、Phase 1-3 の全スキル |
| 移行難易度 | 高 |
| 移行時の変更 | `CLAUDE.md` のワークフロー記述を移行先に合わせて調整 |

**作業**:
1. `.claude/skills/startproject/` ディレクトリごとコピー
2. `CLAUDE.md` のワークフローセクション（`/startproject → /team-implement → /team-review`）を追加
3. 動作確認: `/startproject <小さな機能>` でフル実行
   - Phase 1（UNDERSTAND）: Claude がコードベースを読むか
   - Phase 2（RESEARCH & DESIGN）: Researcher + Architect が起動するか
   - Phase 3（PLAN & APPROVE）: 計画が提示されるか

### 4-2. team-implement

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/team-implement/SKILL.md` |
| 依存 | Agent Teams、タスクリスト（startproject の出力）、品質ツール（ruff/ty/pytest） |
| 移行難易度 | 高 |
| 移行時の変更 | 品質チェックコマンド（`ruff`, `ty`, `pytest`）を移行先のツールに合わせて調整 |

**作業**:
1. `.claude/skills/team-implement/SKILL.md` をコピー
2. SKILL.md 内の品質チェックコマンドを移行先のツールチェインに合わせて調整
3. 動作確認: `/startproject` で作成した計画に対して `/team-implement` を実行

### 4-3. team-review

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/team-review/SKILL.md` |
| 依存 | Agent Teams、Codex CLI、`.claude/rules/security.md`, `coding-principles.md`, `testing.md` |
| 移行難易度 | 高 |
| 移行時の変更 | テスト/カバレッジコマンドを移行先に合わせて調整 |

**作業**:
1. `.claude/skills/team-review/SKILL.md` をコピー
2. テスト/カバレッジコマンドを移行先のツールに合わせて調整
3. 動作確認: 実装後に `/team-review` を実行
   - Security Reviewer が起動するか
   - Quality Reviewer（Codex連携）が起動するか
   - Test Reviewer が起動するか

### Phase 4 完了チェックリスト

- [ ] `/startproject` → `/team-implement` → `/team-review` のフルフローが動作する
- [ ] Agent Teams でチームメイトが正しく起動する
- [ ] Researcher（Gemini）と Architect（Codex）が双方向通信する
- [ ] 並列実装でファイル競合が発生しない
- [ ] レビュー結果が `.claude/docs/research/` に保存される

---

## Phase 5: セッション管理スキル

**目的**: セッションの永続化と初期化スキルを移行する。

### 5-1. checkpointing

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/checkpointing/SKILL.md`, `.claude/skills/checkpointing/checkpoint.py` |
| 依存 | Git、`.claude/logs/cli-tools.jsonl`、`.claude/checkpoints/` |
| 移行難易度 | 中〜高 |
| 移行時の変更 | `checkpoint.py` のパスやログ形式を移行先に合わせて調整が必要 |

**作業**:
1. `.claude/logs/` と `.claude/checkpoints/` ディレクトリを作成
2. `.claude/skills/checkpointing/` ディレクトリごとコピー
3. `checkpoint.py` のパス参照を確認・調整
4. 動作確認: `/checkpointing` でチェックポイントが生成されるか

### 5-2. init

| 項目 | 内容 |
|------|------|
| ファイル | `.claude/skills/init/SKILL.md` |
| 依存 | なし（ただし `AGENTS.md` の存在を期待する） |
| 移行難易度 | 低 |
| 移行時の変更 | `AGENTS.md` → `CLAUDE.md` への参照変更が必要な場合がある |

**注意**: このスキルは移行先リポジトリで最初に実行するものではなく、「新しいプロジェクトをセットアップする時」に使うもの。既存リポジトリへの移行では、実際に使う場面は限定的。

**作業**:
1. `.claude/skills/init/SKILL.md` をコピー
2. 参照先ファイル名（`AGENTS.md` vs `CLAUDE.md`）を確認・調整
3. 動作確認: `/init` で技術スタック検出が動作するか

### Phase 5 完了チェックリスト

- [ ] `/checkpointing` でセッション状態が保存される
- [ ] チェックポイントファイルが `.claude/checkpoints/` に生成される
- [ ] `/init` が動作する（必要に応じて）

---

## CLAUDE.md の移行

全フェーズを通じて、移行先リポジトリの `CLAUDE.md` に以下を段階的に追加する。

### Phase 0 で追加

```markdown
## Language Protocol
- 思考・コード: 英語
- ユーザー対話: 日本語

## Tech Stack
（移行先プロジェクトのツールチェインを記述）
```

### Phase 1 で追加

```markdown
## Documentation
| Location | Content |
|----------|---------|
| `.claude/rules/` | コーディング・セキュリティ・言語ルール |
| `.claude/docs/DESIGN.md` | 設計決定の記録 |
```

### Phase 2 で追加

```markdown
（Documentation テーブルに追加）
| `.claude/docs/libraries/` | ライブラリ制約ドキュメント |
```

### Phase 3 で追加

```markdown
## Why This Exists
| Agent | Strength | Use For |
|-------|----------|---------|
| Claude Code | 1Mコンテキスト、オーケストレーション | 全体統括、コードベース分析 |
| Codex CLI | 深い推論、設計判断 | 設計相談、エラー分析 |
| Gemini CLI | Google Search、マルチモーダル | 外部情報取得、ライブラリ調査 |

（Documentation テーブルに追加）
| `.claude/docs/research/` | 調査結果 |
| `.claude/logs/cli-tools.jsonl` | CLI入出力ログ |
```

### Phase 4 で追加

```markdown
## Workflow
/startproject → /team-implement → /team-review
```

---

## 移行の優先度と見積もり

| Phase | 工数目安 | 価値 | 推奨 |
|-------|---------|------|------|
| Phase 0 | 小 | 高（基盤） | **必須** |
| Phase 1 | 小 | 高（即座に使える） | **必須** |
| Phase 2 | 小 | 中（ドキュメント蓄積） | 推奨 |
| Phase 3 | 中 | 高（AI連携の核心） | **強く推奨**（CLI準備が前提） |
| Phase 4 | 大 | 高（並列開発） | Agent Teams が使える場合 |
| Phase 5 | 中 | 中（長期セッション向け） | 必要に応じて |

---

## 移行時の共通注意点

1. **ツールチェインの差異**: `uv`/`ruff`/`ty`/`pytest` を前提としている記述は移行先に合わせて書き換える
2. **パスのハードコード**: `checkpoint.py` 等にハードコードされたパスがある場合は調整する
3. **CLAUDE.md の競合**: 移行先に既存の `CLAUDE.md` がある場合、マージが必要（上書きしない）
4. **Gitignore**: `.claude/logs/`, `.claude/checkpoints/` を `.gitignore` に追加するか検討
5. **言語ルール**: 日本語対話ルールが不要な場合は `language.md` を調整
