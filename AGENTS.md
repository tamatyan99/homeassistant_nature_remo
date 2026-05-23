# Agent Instructions

## Subagent Usage

When delegating tasks to subagents via the `Agent` tool:

- **Always prefer `run_in_background=true`** when launching subagents, unless the parent agent genuinely requires the result immediately before it can perform any other work.
- While subagents are running in the background, the parent agent should **continue with other work** (e.g., reading files, preparing edits, investigating unrelated parts of the codebase) rather than idly waiting.
- Only block and wait for subagent results when the next step is strictly dependent on their output.

This maximizes parallelism and keeps the session efficient.
