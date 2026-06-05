# GitHub Issues API Notes

## Question

How should a local Python script discover new issues for the current GitHub repository?

## Findings

* Use GitHub REST API rather than GitHub CLI for the MVP because local `gh` is not installed.
* Resolve `owner/repo` from `git remote get-url origin`, with a config or CLI override for repos without a GitHub origin.
* Endpoint shape:
  * `GET /repos/{owner}/{repo}/issues`
  * Useful query params: `state=open`, `sort=created` or `sort=updated`, `direction=desc`, `since=<ISO-8601 timestamp>`, `labels=<comma-separated labels>`, `per_page=100`.
* GitHub's issues endpoint returns pull requests as issue-like records. PR records include `pull_request`; filter those out.
* For private repositories, the request needs a token with repository issue read permission.
* Python can use only the standard library for MVP: `urllib.request`, `json`, and `datetime` are enough.
* Store local state to avoid duplicate processing:
  * `last_seen_at` for incremental polling.
  * `processed_issue_numbers` or per-issue status map.
  * Run directories for generated prompts and logs.

## Recommended MVP Mapping

* `check`:
  * Resolve repo.
  * Fetch open issues.
  * Filter out PRs.
  * Apply label filter if configured.
  * Compare against local state.
  * Print a concise table: issue number, title, labels, created/updated time, URL.

* `generate <issue-number>`:
  * Fetch issue detail.
  * Optionally fetch comments if enabled.
  * Generate `.codex_issue_agent/runs/issue-<N>/goal.md`.
  * Write metadata JSON for auditability.

## Edge Cases

* Rate limit or auth failure should fail before mutating state.
* Closed issues should not be processed by default.
* Edited issues can be regenerated explicitly, but should not silently overwrite prior generated prompt files without a backup or `--force`.
* Prompt injection in issue body must be treated as untrusted input.
