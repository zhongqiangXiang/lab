"""GitHub API client package.

Exports:
    GitHubClient: HTTP client for GitHub REST API
    GitHubAPIError: Exception for API errors
    Issue: GitHub issue data model
    Comment: GitHub issue comment data model
"""

from .client import GitHubClient
from .models import Comment, Issue

class GitHubAPIError(Exception):
    """GitHub API error."""
    pass

__all__ = ["GitHubClient", "GitHubAPIError", "Issue", "Comment"]
