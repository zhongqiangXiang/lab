# issue-codex-automation

English | [简体中文](README.zh-CN.md)

GitHub issue-driven Codex automation tool for safe, controlled code generation from repository issues.

## Overview

`issue-codex-automation` watches GitHub issues in your repository, detects new actionable issues, and generates goal prompts that can be executed by [Codex](https://github.com/anthropics/codex) to implement the requested changes.

**Key features**:
- Label-gated issue eligibility (default: `codex-ready`)
- Safe-mode MVP: generates prompts for manual review before execution
- Local state tracking to avoid duplicate processing
- Built with stdlib only (no external dependencies)

## Installation

```bash
# From repository root
pip install -e .

# Verify installation
issue-codex-automation --version
```

## Configuration

Create a `.env` file in your repository root:

```bash
# Required
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# Optional - auto-detected from git remote if not set
GITHUB_REPO=owner/repo

# Optional defaults
STATE_DIR=.codex_issue_agent
LABEL_FILTER=codex-ready
INCLUDE_COMMENTS=false
```

### Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Yes | - | GitHub personal access token with repo scope |
| `GITHUB_REPO` | No | Auto-detected | Repository in format `owner/repo` |
| `STATE_DIR` | No | `.codex_issue_agent` | Directory for state and run artifacts |
| `LABEL_FILTER` | No | `codex-ready` | Required label for issue eligibility |
| `INCLUDE_COMMENTS` | No | `false` | Include issue comments in generated prompts |

### Getting a GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope (or `public_repo` for public repos only)
3. Copy token and add to `.env`

## Usage

### Workflow Overview

```bash
# Step 1: Discover new eligible issues
issue-codex-automation check

# Step 2: Generate goal prompt for a specific issue
issue-codex-automation generate <issue-number>

# Step 3: Review the generated prompt
cat .codex_issue_agent/runs/issue-<N>/goal.md

# Step 4: Execute with Codex (manual step)
codex exec -C . - < .codex_issue_agent/runs/issue-<N>/goal.md
```

### Commands

#### `check` - Discover eligible issues

Fetches open issues from GitHub and updates local state.

```bash
issue-codex-automation check [--since TIMESTAMP] [--force-refresh]
```

**Options**:
- `--since TIMESTAMP`: Override `last_seen_at` with ISO-8601 timestamp
- `--force-refresh`: Ignore `last_seen_at`, fetch all open issues

**Output**: Table of new issues with number, title, labels, and URL

**Exit codes**:
- `0`: Success
- `1`: Configuration error (missing `GITHUB_TOKEN`, invalid repo)
- `2`: GitHub API error (auth failure, rate limit, network)
- `3`: State file error (corrupt, permission denied)

**Example**:

```bash
$ issue-codex-automation check

INFO: Fetching open issues from owner/repo...
INFO: Found 3 eligible issues

New eligible issues:
----------------------------------------------------------------------------------------------------
#        Title                                              Labels               URL
----------------------------------------------------------------------------------------------------
123      Add user authentication                            codex-ready, feat... https://github.com/...
124      Fix memory leak in parser                          codex-ready, bug     https://github.com/...
125      Update README                                      codex-ready, docs    https://github.com/...
----------------------------------------------------------------------------------------------------
Total: 3 issues
```

#### `generate` - Generate goal prompt

Creates a goal prompt file for a specific issue.

```bash
issue-codex-automation generate <issue-number> [--force] [--no-comments]
```

**Arguments**:
- `issue-number`: GitHub issue number (required)

**Options**:
- `--force`: Overwrite existing `goal.md` if present
- `--no-comments`: Skip fetching comments (overrides `INCLUDE_COMMENTS`)

**Output**:
- `.codex_issue_agent/runs/issue-<N>/goal.md`: Generated prompt
- `.codex_issue_agent/runs/issue-<N>/metadata.json`: Issue metadata
- Prints the `codex exec` command to run

**Exit codes**:
- `0`: Success
- `1`: Configuration error
- `2`: GitHub API error
- `3`: State file error
- `4`: Issue not eligible (missing label, already generated, is PR)
- `5`: Issue not found in state (run `check` first)

**Example**:

```bash
$ issue-codex-automation generate 123

INFO: Fetching issue #123 from GitHub...
INFO: Generating goal prompt...

Generated goal prompt: .codex_issue_agent/runs/issue-123/goal.md
Metadata: .codex_issue_agent/runs/issue-123/metadata.json

To execute with Codex, run:
  codex exec -C . - < .codex_issue_agent/runs/issue-123/goal.md
```

### Global Options

```bash
issue-codex-automation [OPTIONS] COMMAND

Options:
  --config PATH       Path to .env file (default: .env in current directory)
  --state-dir PATH    Override STATE_DIR
  --verbose           Enable debug logging
  --version           Print version and exit
```

## Issue Eligibility

An issue is eligible for code generation if:

1. ✅ State is `open`
2. ✅ Has the configured label (default: `codex-ready`)
3. ✅ Is NOT a pull request
4. ✅ Exists in local state (run `check` to discover)

### Labeling Strategy

Add the `codex-ready` label to issues that are:
- Well-defined with clear requirements
- Safe for automated implementation
- Scoped appropriately (not too broad)

This provides a human approval gate before any goal prompt is generated.

## State Management

State is stored in `STATE_DIR/state.json`:

```json
{
  "last_seen_at": "2024-06-05T10:30:00+00:00",
  "issues": {
    "123": {
      "number": 123,
      "title": "Add user authentication",
      "url": "https://github.com/owner/repo/issues/123",
      "labels": ["codex-ready", "feature"],
      "first_seen": "2024-06-05T10:00:00",
      "last_seen": "2024-06-05T10:30:00",
      "generated": true,
      "generated_at": "2024-06-05T10:35:00"
    }
  }
}
```

### Run Artifacts

Each `generate` creates a run directory:

```
.codex_issue_agent/runs/issue-<N>/
├── goal.md          # Generated prompt (can be edited before execution)
└── metadata.json    # Issue metadata for auditability
```

## Safety Features

### Safe-mode MVP

The MVP does NOT automatically execute Codex. Instead:
1. `check` discovers eligible issues
2. `generate` creates a prompt file
3. **You review the prompt**
4. **You manually run `codex exec`**

This keeps the useful automation while preserving human control over:
- Prompt quality
- Scope validation
- Repository safety

### Prompt Injection Protection

Issue bodies and comments are treated as untrusted input:
- Wrapped in fenced code blocks
- Clear instructions to follow project guidelines over issue text
- Stop conditions for ambiguous requirements

### Validation Gates

The `generate` command validates:
- Issue has required label
- Issue is open (not closed)
- Issue is not a pull request
- Working tree state before suggesting execution

## Troubleshooting

### "GITHUB_TOKEN is required"

Set `GITHUB_TOKEN` in your `.env` file or environment:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
```

### "Could not detect repository from git remote"

Either:
- Ensure `git remote get-url origin` points to a GitHub repository
- Set `GITHUB_REPO` in `.env`:

```bash
GITHUB_REPO=owner/repo
```

### "Authentication failed"

Your `GITHUB_TOKEN` is invalid or lacks required permissions. Generate a new token with `repo` scope.

### "API rate limit exceeded"

GitHub API rate limits:
- **Authenticated**: 5,000 requests/hour
- **Unauthenticated**: 60 requests/hour

Wait for rate limit reset or use a token with higher limits.

### "Issue not found in state"

Run `check` first to discover and track the issue:

```bash
issue-codex-automation check
issue-codex-automation generate <issue-number>
```

## Future Enhancements

The safe-mode MVP establishes the foundation. Future versions could add:

- **Automatic execution**: `run` command to execute Codex directly
- **Branch isolation**: Create feature branches per issue
- **PR creation**: Automatically open pull requests after successful runs
- **Issue comments**: Report status back to GitHub
- **Richer routing**: Label-driven agent selection or configuration
- **Validation hooks**: Pre-execution checks (dirty worktree, test baseline)
- **Audit logs**: Detailed execution logs per run

## License

MIT License - see LICENSE file for details
