# Codex CLI Boundary Notes

## Question

How should the script hand generated issue goals to local Codex safely?

## Findings

* Local `codex` exists at `/usr/local/bin/codex`.
* Local `codexs` was not found in `PATH`.
* `codex exec` supports non-interactive execution.
* Relevant `codex exec` options from local help:
  * `-C, --cd <DIR>`: set working root.
  * Prompt can be read from stdin when prompt is omitted or `-` is used.
  * `--json`: print JSONL events.
  * `-o, --output-last-message <FILE>`: save final response.
  * `-s, --sandbox <MODE>` and `-a, --ask-for-approval <POLICY>` control execution safety.

## Recommended MVP Mapping

Safe-mode MVP should not launch Codex automatically. It should print a command like:

```bash
codex exec -C /path/to/repo - < .codex_issue_agent/runs/issue-123/goal.md
```

If a future explicit `run` command is added, use:

```bash
codex exec -C /path/to/repo --json -o .codex_issue_agent/runs/issue-123/final.txt - < .codex_issue_agent/runs/issue-123/goal.md
```

## Important Unknown

`/goal` is a Codex slash command intended for interactive persistent goals. It must be validated whether `codex exec` interprets `/goal` or treats it as plain prompt text. Until validated, the generated file should be useful both ways:

* start with a `/goal ...` command for interactive copy/paste;
* include the full 5-section objective/scope/constraints/done/stop structure so it can also work as a normal `codex exec` prompt.

## Edge Cases

* Dirty worktree should be surfaced before suggesting a Codex command.
* The command should not include dangerous sandbox bypass flags by default.
* Generated prompt should include issue body as quoted source material, not as instructions that can override project rules.
* Logs and generated prompts should be stored under a tool-owned directory for auditability.
