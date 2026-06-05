# Issue-driven Codex Automation Feasibility

## Goal

Analyze and shape a feasible Python automation script that watches the current repository's GitHub issues, detects new actionable issues, pulls issue content, turns that content into an audit-friendly `/goal` prompt using the `goal-prompt-builder` skill pattern, and launches local Codex to implement the requested code changes.

## What I Already Know

* User wants a Python script that loops over the current repository's issues and reacts to newly appearing issues.
* For each new issue, the script should fetch the issue content and use the `goal-prompt-builder` skill plus the issue body to generate a `/goal` prompt.
* The generated `/goal` prompt should then be passed to local Codex so Codex performs the implementation.
* Current local repo is a minimal Trellis/Codex lab repository, not yet a Python package.
* Local `codex` CLI exists at `/usr/local/bin/codex`.
* Local `codexs` command was not found in `PATH`.
* Local `gh` command was not found in `PATH`; the script should not depend on GitHub CLI unless that becomes an explicit requirement.
* Current repo has `AGENTS.md`, `.trellis/`, `.codex/`, and `.agents/` project context.

## Assumptions (Temporary)

* "Current repository issues" means GitHub issues for the Git remote associated with the working directory.
* The script can use `GITHUB_TOKEN` or another environment variable for authenticated API access.
* The script may create local state files, such as `.codex_issue_agent/state.json`, to remember processed issue IDs.
* The script should default to a conservative dry-run or review-first mode before allowing autonomous code changes.
* The `goal-prompt-builder` skill does not expose a standalone executable; the script will need either a deterministic template renderer or a Codex prompt that instructs Codex to apply that skill.

## Open Questions

* None.

## Requirements (Evolving)

* Discover repository owner/name from `git remote get-url origin`, with an explicit config override.
* Poll GitHub issues using GitHub REST API, not `gh`, because `gh` is not installed locally.
* Track processed issues in a durable local state file to avoid duplicate runs.
* Ignore pull requests returned by the Issues API.
* Extract issue number, title, body, labels, URL, author, created/updated timestamps, and comments if configured.
* Generate `/goal` text with clear Objective, Scope, Constraints, Done when, Stop if, and token budget.
* Launch Codex through the installed `codex` command, likely `codex exec -C <repo> -` for non-interactive automation.
* Validate whether `codex exec` executes `/goal` slash commands or treats them as plain prompt text.
* If `codex exec` does not support `/goal`, use the `goal-prompt-builder` structure as a normal `codex exec` prompt, or use an interactive/remote-control Codex channel for true `/goal` sessions.
* Capture each run's prompt, Codex output, exit code, and artifacts in a per-issue run directory.
* Expose a two-step CLI for the safe-mode MVP:
  * `check`: list eligible new issues and persist/update local discovery state.
  * `generate <issue-number>`: fetch the selected issue, generate the goal prompt file and metadata, then print the manual Codex command.
* Use label-gated issue eligibility in the MVP:
  * Only open issues with the configured label `codex-ready` are eligible.
  * Pull requests are still ignored even if they carry the label.
  * `generate <issue-number>` should reject issues missing the configured label unless a future explicit override flag is added.

## Acceptance Criteria (Evolving)

* [ ] The feasibility analysis identifies required dependencies, command boundaries, and missing local tools.
* [ ] The recommended MVP includes a human approval gate or other safety control before code-changing automation.
* [ ] The design accounts for duplicate detection, PR filtering, rate limits, authentication, dirty worktrees, and failed Codex runs.
* [ ] The design includes a concrete command flow for `codex exec`.
* [ ] The safe-mode CLI exposes `check` and `generate <issue-number>` commands.
* [ ] The issue eligibility gate defaults to label `codex-ready`.
* [ ] The PRD captures out-of-scope automation that should not be built in the first pass.

## Definition of Done (Team Quality Bar)

* Tests added/updated if implementation proceeds.
* Lint/typecheck/test commands pass once a Python project structure exists.
* Docs/notes updated if behavior changes.
* Rollout/rollback considered because this automates code modification.

## Technical Approach

Recommended direction: build a two-stage automation with a conservative approval gate.

MVP mode: **safe mode**. The script discovers eligible new issues, generates a `/goal` prompt file plus run metadata, and prints the exact Codex command for the user to run manually. It does not automatically start Codex in the first version unless the user later opts into a separate explicit command.

CLI shape: **two-step command flow**. Use `check` to discover candidates and `generate <issue-number>` to create a goal for one selected issue. This keeps the safe-mode boundary explicit and makes each step easy to test.

Eligibility: **label-gated**. The MVP only processes open issues with readiness label `codex-ready`. This gives the repository a clear human approval signal before any `/goal` prompt is generated.

1. Poller stage:
   * Resolve repo identity.
   * Fetch open issues via GitHub REST API with `state=open`, `sort=created` or `sort=updated`, `direction=desc`, and optional `since`.
   * Filter out entries containing `pull_request`.
   * Filter labels to `codex-ready`.
   * Compare issue IDs/numbers against local state.

2. Prompt generation stage:
   * Render a `/goal` using the `goal-prompt-builder` 5-section structure.
   * Include issue URL and issue title/body as source material.
   * Add repository constraints from `AGENTS.md`.
   * Add stop conditions for dirty worktree, missing tests, ambiguous issue scope, new dependencies, and existing tests failing.

3. Codex execution stage:
   * In safe MVP mode, write the generated goal to disk and print the exact next command, for example `codex exec -C <repo> - < <goal-file>`.
   * Do not run Codex automatically in the first MVP.
   * If a later explicit `run` command is added, run `codex exec -C <repo> -` with the generated prompt on stdin and capture logs per issue.

## Decision (ADR-lite)

**Context**: The desired system can modify code in response to external issue text, which is powerful but unsafe if it runs on arbitrary issues without filtering or approval.

**Decision**: Treat the first MVP as an issue-to-goal generator in safe mode, not a fully autonomous issue-to-Codex runner.

**Consequences**: This keeps the useful automation while preserving human control over scope, prompt quality, and repository safety. Later versions can add explicit Codex execution, labels, assignment rules, branch isolation, PR creation, and issue comments.

## Out of Scope

* Automatically pushing branches or opening pull requests.
* Automatically closing or commenting on issues.
* Running on every issue without label or approval filtering.
* Automatically starting Codex as part of the first safe-mode MVP.
* Generating goals for issues missing the configured readiness label.
* Supporting non-GitHub issue trackers.
* Full daemon/service packaging with launchd/systemd.
* Reliance on `gh` or `codexs` unless those tools are installed and explicitly chosen.

## Expansion Sweep

### Future Evolution

* Add richer label-driven routing beyond the initial `codex-ready` gate.
* Add branch-per-issue and PR creation after successful Codex implementation.

### Related Scenarios

* Issue body could contain a ready-made `/goal`; in that case prompt generation should validate rather than rewrite it.
* Existing Trellis tasks could be created per issue before Codex runs.

### Failure & Edge Cases

* GitHub API rate limiting, auth failure, private repo permissions, network timeouts.
* Dirty worktree before Codex starts.
* Issue is edited, closed, or unlabelled while the script is processing.
* Codex exits non-zero, asks for unavailable permissions, or modifies files outside expected scope.
* Prompt injection in issue body tries to override repository instructions.

## Research References

* [`research/github-issues-api.md`](research/github-issues-api.md) — Use GitHub REST issues API directly, filter PR records, store local state, and generate per-issue run artifacts.
* [`research/codex-cli-boundary.md`](research/codex-cli-boundary.md) — Use safe-mode prompt generation first; print `codex exec` command instead of running Codex automatically.

## Technical Notes

* `fast_context_search` could not run because `WINDSURF_API_KEY` is unavailable.
* Local `command -v` found `codex` and `python3`; it did not find `codexs` or `gh`.
* The installed `codex exec` is the realistic command surface for automation.
* True `/goal` persistence may require an interactive Codex session; this must be validated before depending on `codex exec` for slash-command behavior.
* If implementation proceeds, create a Python package/script structure first because the repository currently has only README/AGENTS/Trellis/Codex config files.
