"""Custom exception hierarchy for issue_codex_automation."""


class IssueCodexError(Exception):
    """Base exception for all issue_codex_automation errors."""
    pass


class ConfigurationError(IssueCodexError):
    """Raised when configuration is invalid or missing required fields."""
    pass


class GitHubAPIError(IssueCodexError):
    """Raised when GitHub API requests fail."""
    pass


class StateError(IssueCodexError):
    """Raised when state file operations fail."""
    pass


class RepositoryError(IssueCodexError):
    """Raised when repository detection or validation fails."""
    pass
