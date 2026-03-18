---
name: fs-ops
description: |
  Filesystem operations skill with impact analysis. Handles mkdir, rm, cp, mv,
  chmod, ln, touch, and directory restructuring. Checks impact scope before
  executing, with risk-based confirmation flow.
  Requires feature/* branch. All operations are logged to .claude/logs/fs-ops.jsonl.
context: fork
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion
metadata:
  short-description: Filesystem operations with impact analysis
---

# Filesystem Operations

**ファイルシステム操作を影響範囲チェック付きで実行するスキル。**

## Prerequisites

### Branch Restriction (MUST)

**`feature/*` ブランチでのみ操作可能。それ以外のブランチでは実行を拒否する。**

スキル起動直後に以下を実行:

```bash
git branch --show-current
```

- `feature/*` にマッチする場合 → 続行
- それ以外（`main`, `develop`, `hotfix/*` 等）→ **即座に中断**し、以下を報告:

```
⛔ fs-ops は feature/* ブランチでのみ実行できます。
現在のブランチ: {branch_name}

feature ブランチに切り替えてから再実行してください。
```

**例外なし。`--force` 等のオプションでもバイパスできない。**

## Risk Classification

操作をリスクレベルで分類し、レベルに応じた事前チェックを行う。

| Risk | Operations | Pre-check |
|------|-----------|-----------|
| **Low** | `mkdir`, `touch`, `ls`, `tree`, `du`, `df` | なし（即実行） |
| **Medium** | `cp`, `mv`, `ln`, `rename` | 対象確認 + 参照影響チェック |
| **High** | `rm`, `rm -rf`, `chmod`, `chown`, `rmdir` | ファイル一覧 + git 状態 + ユーザー確認必須 |

## Workflow

```
Step 0: Branch check → feature/* でなければ中断
  ↓
Step 1: Parse user request → identify operation + targets
  ↓
Step 2: Classify risk level
  ↓
Step 3: Impact analysis (Medium/High only)
  ↓
Step 4: Show impact report + confirm (Medium/High only)
  ↓
Step 5: Execute operation
  ↓
Step 6: Log to .claude/logs/fs-ops.jsonl
  ↓
Step 7: Report result
```

---

## Step 0: Branch Check

```bash
branch=$(git branch --show-current)
```

`feature/*` パターンにマッチしない場合は即中断。Step 1 以降に進まない。

## Step 1: Parse Request

ユーザーの要求から以下を特定する:

- **操作種別**: mkdir, rm, cp, mv, etc.
- **対象パス**: ファイル/ディレクトリのパス（複数可）
- **オプション**: `-r`, `-f`, `-p` 等のフラグ

## Step 2: Classify Risk

上記の Risk Classification テーブルに基づいてリスクレベルを判定する。

追加ルール:
- `rm` に `-rf` や `-r` が付く場合 → **High**
- `mv` でディレクトリを対象とする場合 → **High** に昇格
- ワイルドカード (`*`, `**`) を含む操作 → 1段階昇格
- プロジェクトルート直下の操作 → 1段階昇格

## Step 3: Impact Analysis

### Low Risk

チェック不要。Step 5 へ進む。

### Medium Risk (`cp`, `mv`, `ln`, `rename`)

```bash
# 1. 対象ファイルの存在確認
ls -la {target_path}

# 2. 上書き対象の確認（cp, mv の場合）
ls -la {destination_path} 2>/dev/null

# 3. 参照影響チェック（mv, rename の場合）
# - import 文やパス参照を検索
```

参照影響チェックでは Grep ツールで以下を検索:
- 対象ファイル名を含む import 文
- 対象パスを文字列として参照しているコード
- 設定ファイル内のパス参照

### High Risk (`rm`, `rm -rf`, `chmod`, `chown`)

```bash
# 1. 対象ファイル/ディレクトリの一覧
ls -la {target_path}
# ディレクトリの場合はツリー表示
find {target_path} -type f | head -50

# 2. git 追跡状態の確認
git ls-files {target_path}
git status {target_path}

# 3. ファイルサイズ・数の集計
du -sh {target_path}
find {target_path} -type f | wc -l

# 4. 参照影響チェック（rm の場合）
# - 対象ファイルを参照しているコードを検索
```

## Step 4: Impact Report + Confirmation

Medium/High の場合、影響範囲レポートを表示してユーザーに確認を取る。

### Report Format

```markdown
## 影響範囲レポート

### 操作
{operation} {target_path}

### リスクレベル: {Low/Medium/High}

### 対象
- ファイル数: {count}
- 合計サイズ: {size}
- git 追跡: {tracked_count} ファイル

### 参照への影響
- {file1}:{line} — {matched_line}
- {file2}:{line} — {matched_line}
（参照なしの場合: 「参照は見つかりませんでした」）

### 実行するコマンド
`{actual_command}`
```

**High Risk の場合は必ず `AskUserQuestion` でユーザーの明示的な承認を得る。**

承認なしでの実行は禁止。

## Step 5: Execute

承認を得た（またはLow Riskの）操作を実行する。

```bash
# 実行
{command}

# 実行後の状態確認
ls -la {target_or_parent_path}
```

### Safety Guards

- `rm -rf /` や `rm -rf ~` 等のシステム破壊コマンドは**絶対に実行しない**
- **パス正規化（MUST）**: 操作実行前に `realpath` で対象パスを正規化し、プロジェクトルートの接頭辞と一致するか検証する:
  ```bash
  # パス検証手順
  project_root=$(git rev-parse --show-toplevel)
  resolved_path=$(realpath -m "$target_path")
  # resolved_path が project_root で始まるか検証
  # 不一致の場合は即中断（シンボリックリンク経由の脱出を防止）
  ```
- プロジェクトルートより上のパスへの操作は拒否する
- `.git/` ディレクトリ内の操作は拒否する（git コマンドで行うべき）
- **Secrets ファイル操作時の必須確認**: `.env`, `credentials.json`, `*.key`, `*.pem`, `*.secret`, `*credentials*` 等の secrets パターンに該当するファイルの操作（特に削除・移動）は、`AskUserQuestion` で明示的なユーザー確認を**必須**とする。確認なしでの実行は禁止

## Step 6: Log Operation (MUST)

**全ての操作（成功・失敗を問わず）を `.claude/logs/fs-ops.jsonl` に追記する。**

このステップは必須。スキップ不可。

### Log Format (JSONL)

1行1エントリの JSON Lines 形式で追記する:

```bash
echo '{"timestamp":"YYYY-MM-DDTHH:MM:SS+00:00","branch":"feature/xxx","operation":"mkdir","command":"mkdir -p src/utils","targets":["src/utils"],"risk":"low","impact_summary":null,"user_confirmed":false,"success":true,"error":null}' >> .claude/logs/fs-ops.jsonl
```

### Log Entry Schema

```json
{
  "timestamp": "ISO 8601 timestamp (UTC)",
  "branch": "current git branch name",
  "operation": "mkdir|rm|cp|mv|ln|chmod|chown|touch|rmdir|rename",
  "command": "actual command executed",
  "targets": ["list", "of", "target", "paths"],
  "risk": "low|medium|high",
  "impact_summary": "impact analysis summary string (null for low risk)",
  "user_confirmed": true/false,
  "success": true/false,
  "error": "error message if failed (null if success)"
}
```

### Logging Rules

- **成功・失敗の両方をログする**（`success` フィールドで区別）
- **ブランチチェックで拒否された場合はログしない**（操作自体が発生していないため）
- **ユーザーが Impact Report で拒否した場合もログする**（`success: false`, `error: "user_rejected"`）
- タイムスタンプは `date -u +%Y-%m-%dT%H:%M:%S+00:00` で取得
- ファイルが存在しない場合は自動作成される（`>>` による追記）

## Step 7: Result Report

```markdown
## 完了: {operation}

- 操作: `{command}`
- ブランチ: `{branch_name}`
- リスク: {Low/Medium/High}
- 結果: {success/failure}
- 変更内容:
  - {created/deleted/moved/copied}: {path}
- ログ: `.claude/logs/fs-ops.jsonl` に記録済み
```

---

## Examples

### mkdir（Low Risk — 即実行）

```
ユーザー: src/utils ディレクトリを作って
→ Step 0: git branch → feature/add-utils ✓
→ mkdir -p src/utils
→ fs-ops.jsonl にログ追記
→ 結果を報告
```

### mv（Medium Risk — 影響確認）

```
ユーザー: src/helpers.py を src/utils/helpers.py に移動して
→ Step 0: git branch → feature/refactor ✓
→ 参照影響チェック（import helpers を検索）
→ 影響レポート表示
→ ユーザー確認後に実行
→ fs-ops.jsonl にログ追記
→ 結果を報告
```

### rm -rf（High Risk — 必須確認）

```
ユーザー: tmp/ ディレクトリを削除して
→ Step 0: git branch → feature/cleanup ✓
→ ファイル一覧 + git 状態 + サイズ確認
→ 影響レポート表示
→ AskUserQuestion で明示的な承認を取得
→ 承認後に実行
→ fs-ops.jsonl にログ追記
→ 結果を報告
```

### Branch rejection

```
ユーザー: tmp/ を削除して
→ Step 0: git branch → main ✗
→ ⛔ 中断。feature/* ブランチへの切り替えを案内
```

---

## Don't-Ask Mode

**don't-ask モード（`--dangerously-skip-permissions` / `mode: dontAsk` / `mode: auto`）で実行中の場合、リスクレベルに応じてユーザー確認をスキップする。**

| 確認ポイント | 通常モード | Don't-Ask モード |
|------------|-----------|-----------------|
| Step 4: Low Risk 操作 | 確認なし（即実行） | 変更なし（常に即実行） |
| Step 4: Medium Risk 操作 | 影響レポート表示 + 確認 | 影響レポートを出力するが確認をスキップし自動実行 |
| Step 4: High Risk 操作 | 影響レポート表示 + `AskUserQuestion` で必須確認 | **確認を維持（スキップしない）** -- High Risk は常にユーザー確認必須 |
| Secrets ファイル操作の確認 | `AskUserQuestion` で必須確認 | **確認を維持（スキップしない）** -- Secrets 操作は常にユーザー確認必須 |

### 重要な制約

- **High Risk 操作（`rm`, `rm -rf`, `chmod`, `chown`）は don't-ask モードでもユーザー確認を省略しない**。データ損失・権限変更リスクがあるため例外なし。
- **Secrets ファイルの操作は don't-ask モードでもユーザー確認を省略しない**。
- **`feature/*` ブランチ制約は don't-ask モードでもバイパスできない**。
- **ログ記録（Step 6）は don't-ask モードでもスキップしない**。
- **Safety Guards（パス正規化、プロジェクトルート外の操作拒否、`.git/` 操作拒否）は don't-ask モードでもバイパスできない**。

---

## Tips

- `context: fork` で実行されるため、メインコンテキストは汚染されない
- 複数操作を一括で要求された場合、各操作のリスクを個別に評価する
- 参照影響チェックは Grep ツールで高速に実行する
- ユーザーが「確認なしで」と明示した場合でも、High Risk 操作は確認を省略しない
- ログは `cat .claude/logs/fs-ops.jsonl | python -m json.tool` で整形表示可能
- `feature/*` 制約により、main/develop への直接的なファイル操作事故を防止する
