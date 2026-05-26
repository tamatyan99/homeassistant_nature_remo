# Agent Instructions

## Subagent Usage

サブエージェント（Agent tool）を呼び出す際は、**原則として `run_in_background=true` を設定してください**。

### 背景タスクを優先する理由
- 複数のサブエージェントを並行して起動でき、総処理時間を短縮できる
- 親エージェントはフォアグラウンドで他の作業を継続できる

### 正しい使い方（完了順処理 + 依存関係管理）
ユーザーから1つの指示を受け、それを複数のサブエージェントに分割する場合は、以下の流れで実行してください：

1. **バックグラウンドですべてのサブエージェントを並列起動する**
2. **`TaskList` または `TaskOutput(block=false)` で各タスクの状態をポーリングし、完了したものから順に結果を取得する**
3. **取得した結果は、他のサブエージェントの結果に依存しないかチェックし、独立していればすぐに処理する**
4. **他のサブエージェントの結果が必要な場合は、そのタスクが完了して結果が揃うまで待つ（`TaskOutput(block=true)` で特定のタスクをブロッキング待ち）**
5. すべてのタスクが完了し、すべての処理が終わったら、まとめて応答を返してターンを終了する

**⭕ 正しい例（独立したタスク）：**
```
Agent(レビュー1, run_in_background=true)
Agent(レビュー2, run_in_background=true)
Agent(レビュー3, run_in_background=true)

→ TaskList または TaskOutput(block=false) で状態を確認
→ レビュー2が先に完了 → 結果を取得 → すぐに処理
→ レビュー1が次に完了 → 結果を取得 → すぐに処理
→ レビュー3が最後に完了 → 結果を取得 → すぐに処理
→ すべて処理完了後、まとめて応答を返してターンを終了
```

**⭕ 正しい例（依存関係があるタスク）：**
```
Agent(設計レビュー, run_in_background=true)
Agent(実装レビュー, run_in_background=true)

→ 完了順に結果を取得
→ 実装レビューが先に完了 → 独立して処理可能ならすぐに処理
→ 設計レビューが完了 → 実装レビューの結果が設計レビューの修正に必要な場合：
  → 実装レビューの結果を前提として設計レビューの修正を実行
→ すべて処理完了後、まとめて応答を返してターンを終了
```

### 絶対に守るべきルール
- **「待っています」「完了を待ちます」などの待機宣言をしてはいけない**。能動的にポーリングし、完了したものから順に処理を進めているのだから、待機宣言は不要である
- **すべてのサブエージェントの処理が完結するまで、親エージェントはターンを終了してはいけない**
- **取得した結果は即座に処理すること**。取得しておいて後でまとめて処理してはいけない。完了順に、フォアグラウンドでできる作業を進める
- **依存関係を事前に把握すること**。どのサブエージェントの結果が、どの処理の前提になるかを計画し、前提が揃った順に処理を実行する
- **1つのユーザー指示は、1ターン内で完結させる**

### フォアグラウンドで実行すべき例外ケース
以下の場合のみ `run_in_background=false`（または省略）を許容します：
- 単一のサブエージェント呼び出しのみで、並列化のメリットがない場合
- 短時間（数秒以内）で確実に完了する単純な確認・照会のみの場合
- 子エージェント自身がフォアグラウンドで実行されている場合

## Development Rules

- **Never commit `venv/`** — The virtual environment is local-only and already excluded in `.gitignore`.
- **Run tests** with `python -m pytest tests/ -v` before committing test-related changes.
- **Bump `manifest.json` version** on every release to force Home Assistant cache invalidation.
- **Delete `__pycache__`** in `custom_components/nature_remo/` after major refactors before restarting HA, to avoid stale bytecode errors.
