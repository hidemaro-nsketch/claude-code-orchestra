# Decision Log: git-history-routing

### [startproject] DECISION — 2026-02-19

- **担当者**: ユーザー + Claude Lead
- **概要**: git 履歴をたどる操作（git log, git blame, git show, git bisect, git reflog 等）は全般的にサブエージェント経由で Gemini に委託するルールとする
- **理由**: git 履歴操作は出力が大きくなりやすく、Gemini の分析能力を活用すべき。場面を限定せず全般的なルーティングルールとして定義する
- **ステータス**: 承認済み

### [startproject] DECISION — 2026-02-19

- **担当者**: ユーザー + Claude Lead
- **概要**: 変更対象は CLAUDE.md, tool-routing.md, startproject skill, gemini-delegation.md, enforce-tool-routing.py
- **理由**: 全関連ドキュメントに一貫して記載することで、ルールの明確性を確保する
- **ステータス**: 承認済み

### [startproject] DECISION — 2026-02-19

- **担当者**: ユーザー + Claude Lead
- **概要**: Linear タスクへの紐付けはスキップ（ユーザー確認済み）
- **理由**: ユーザーがスキップを選択
- **ステータス**: 承認済み

### [startproject] PRE — 2026-02-19

- **担当者**: Claude Lead
- **概要**: プロジェクト概要書を作成（git-history-routing）
- **成果物**: `.claude/docs/decisions/brief-git-history-routing.md`

### [startproject] POST — 2026-02-19

- **担当者**: Claude Lead
- **概要**: 計画フェーズ完了、5ファイルに git 履歴ルーティングルールを追記。Linear スキップ（ユーザー確認済み）
- **成果物**:
  - `CLAUDE.md`（Git 履歴探索行を追加）
  - `.claude/rules/tool-routing.md`（Git History Analysis セクション新設）
  - `.claude/rules/gemini-delegation.md`（ユースケース・トリガー追加）
  - `.claude/skills/startproject/SKILL.md`（Phase 1 に指針追加）
  - `.claude/hooks/enforce-tool-routing.py`（blame/show/bisect/reflog/shortlog を登録）
