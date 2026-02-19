## Project Brief: git-history-routing

### Current State
- `tool-routing.md` の Git Operations セクションに `git log`, `git diff` 等は記載済みだが、`git blame`, `git show`, `git bisect`, `git reflog` 等の履歴探索コマンドは明示的に記載されていない
- `enforce-tool-routing.py` の `ROUTED_GIT_SUBCOMMANDS` にも `blame`, `show`, `bisect`, `reflog` は未登録（catch-all で警告は出る）
- `CLAUDE.md` の Tool Routing テーブルにも履歴探索コマンドの明示的な記載なし
- `startproject` skill の Phase 1 に git 履歴を活用する指針なし
- `gemini-delegation.md` に git 履歴分析のユースケース記載なし

### Goal
git 履歴をたどる操作が必要となった場合、サブエージェントで Gemini に委託するルールを全関連ファイルに一貫して記載する。

### Scope
- Include: CLAUDE.md, tool-routing.md, startproject skill, gemini-delegation.md, enforce-tool-routing.py
- Exclude: 他のスキル（team-implement, team-review, deploy 等）は今回の対象外

### Constraints
- 既存のルーティングルールとの整合性を保つ
- S tier タスクとして最小限の変更に留める

### Success Criteria
- 全関連ファイルに git 履歴操作のルーティングルールが記載されている
- enforce-tool-routing.py に履歴コマンドが明示的に登録されている
- 既存ルールとの矛盾がない
