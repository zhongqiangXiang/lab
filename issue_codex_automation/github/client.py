"""HTTP client for GitHub REST API v3.

This module provides a client for interacting with the GitHub Issues API,
including authentication, rate limiting, and error handling.
"""

import json
import os
import time
from typing import List, Optional, Union, Dict
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .models import Issue, Comment
from ..errors import GitHubAPIError, ConfigurationError


class GitHubClient:
    """GitHub REST API v3 client for issue operations.

    Handles authentication, rate limiting, and common error scenarios.

    Attributes:
        token: GitHub personal access token for authentication
        base_url: Base URL for GitHub API (defaults to api.github.com)
    """

    def __init__(self, token: Optional[str] = None, base_url: str = "https://api.github.com"):
        """Initialize GitHub API client.

        Args:
            token: GitHub token (reads from GITHUB_TOKEN env var if not provided)
            base_url: GitHub API base URL (for testing or GitHub Enterprise)

        Raises:
            ConfigurationError: If no token is provided or found in environment
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ConfigurationError(
                "GitHub token not provided. Set GITHUB_TOKEN environment variable "
                "or pass token parameter."
            )

        # Enforce HTTPS for security
        if not base_url.startswith("https://"):
            raise ConfigurationError(
                f"Invalid base_url: must use HTTPS. Got: {base_url}"
            )

        self.base_url = base_url.rstrip("/")

    def __repr__(self) -> str:
        """Safe string representation that doesn't expose token."""
        return f"GitHubClient(base_url='{self.base_url}', token='***')"

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        retry_on_rate_limit: bool = True,
    ) -> Union[Dict, List]:
        """Make authenticated HTTP request to GitHub API.

        Args:
            endpoint: API endpoint path (e.g., "/repos/owner/repo/issues")
            params: Query parameters dictionary
            retry_on_rate_limit: If True, wait and retry when rate limited

        Returns:
            Parsed JSON response (dict or list)

        Raises:
            GitHubAPIError: On HTTP errors or API failures
        """
        url = f"{self.base_url}{endpoint}"

        # Build query string
        if params:
            query_parts = []
            for key, value in params.items():
                if value is not None:
                    query_parts.append(f"{key}={value}")
            if query_parts:
                url = f"{url}?{'&'.join(query_parts)}"

        # Validate token doesn't contain injection characters
        if any(c in self.token for c in ['\n', '\r', '\0']):
            raise GitHubAPIError("Invalid token: contains control characters")

        # Create request with headers
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "issue-codex-automation/0.1.0",
        }
        request = Request(url, headers=headers)

        try:
            with urlopen(request, timeout=30) as response:
                data = response.read().decode("utf-8")
                return json.loads(data)

        except HTTPError as e:
            status_code = e.code
            error_body = e.read().decode("utf-8", errors="replace")

            # Parse error message from response
            try:
                error_data = json.loads(error_body)
                error_message = error_data.get("message", error_body)
            except (json.JSONDecodeError, KeyError):
                error_message = error_body or e.reason

            # Handle rate limiting with retry
            if status_code == 403:
                # Check if this is a rate limit error
                if "rate limit" in error_message.lower():
                    retry_after = e.headers.get("Retry-After")
                    x_ratelimit_reset = e.headers.get("X-RateLimit-Reset")

                    if retry_on_rate_limit and (retry_after or x_ratelimit_reset):
                        # Calculate wait time
                        if retry_after:
                            wait_seconds = int(retry_after)
                        elif x_ratelimit_reset:
                            reset_time = int(x_ratelimit_reset)
                            wait_seconds = max(0, reset_time - int(time.time()))
                        else:
                            wait_seconds = 60  # Default fallback

                        raise GitHubAPIError(
                            f"Rate limit exceeded. Retry after {wait_seconds} seconds.",
                            status_code=status_code,
                        )

                # Generic 403 error (permissions, not rate limit)
                raise GitHubAPIError(
                    f"Access forbidden: {error_message}. Check token permissions.",
                    status_code=status_code,
                )

            # Handle authentication errors
            if status_code == 401:
                raise GitHubAPIError(
                    f"Authentication failed: {error_message}. Check GITHUB_TOKEN.",
                    status_code=status_code,
                )

            # Handle not found errors
            if status_code == 404:
                raise GitHubAPIError(
                    f"Resource not found: {error_message}. Check repository access.",
                    status_code=status_code,
                )

            # Generic HTTP error
            raise GitHubAPIError(
                f"GitHub API error ({status_code}): {error_message}",
                status_code=status_code,
            )

        except URLError as e:
            raise GitHubAPIError(f"Network error: {e.reason}")

        except json.JSONDecodeError as e:
            raise GitHubAPIError(f"Failed to parse GitHub API response: {e}")

        except Exception as e:
            raise GitHubAPIError(f"Unexpected error: {e}")

    def get_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: Optional[str] = None,
        since: Optional[str] = None,
        per_page: int = 100,
    ) -> List[Issue]:
        """Fetch issues from a repository.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            state: Issue state filter ("open", "closed", "all")
            labels: Comma-separated label names to filter by
            since: ISO 8601 timestamp to filter issues updated after this time
            per_page: Results per page (max 100)

        Returns:
            List of Issue objects (excludes pull requests)

        Raises:
            GitHubAPIError: On API errors
            ValueError: If parameters are invalid
        """
        if state not in ("open", "closed", "all"):
            raise ValueError(f"Invalid state: {state}. Must be 'open', 'closed', or 'all'.")

        if per_page < 1 or per_page > 100:
            raise ValueError(f"Invalid per_page: {per_page}. Must be between 1 and 100.")

        endpoint = f"/repos/{owner}/{repo}/issues"
        params = {
            "state": state,
            "per_page": str(per_page),
            "sort": "updated",
            "direction": "desc",
        }

        if labels:
            params["labels"] = labels

        if since:
            params["since"] = since

        response = self._make_request(endpoint, params)

        if not isinstance(response, list):
            raise GitHubAPIError("Expected list response from issues endpoint")

        # Parse and filter out pull requests
        issues = []
        for item in response:
            try:
                issue = Issue.from_json(item)
                # Filter out pull requests
                if not issue.is_pull_request:
                    issues.append(issue)
            except (KeyError, TypeError, ValueError) as e:
                # Log parsing error but continue with other issues
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to parse issue from API response: {e}")
                continue

        return issues

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Issue:
        """Fetch a single issue by number.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            Issue object

        Raises:
            GitHubAPIError: On API errors or if issue is a pull request
            ValueError: If issue_number is invalid
        """
        if issue_number < 1:
            raise ValueError(f"Invalid issue_number: {issue_number}. Must be positive.")

        endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}"
        response = self._make_request(endpoint)

        if not isinstance(response, dict):
            raise GitHubAPIError("Expected dict response from issue endpoint")

        try:
            issue = Issue.from_json(response)
        except (KeyError, TypeError, ValueError) as e:
            raise GitHubAPIError(f"Failed to parse issue response: {e}")

        # Reject pull requests
        if issue.is_pull_request:
            raise GitHubAPIError(
                f"Issue #{issue_number} is a pull request. Use pull request API instead.",
                status_code=400,
            )

        return issue

    def get_issue_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int,
    ) -> List[Comment]:
        """Fetch comments for an issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            List of Comment objects (sorted by creation time)

        Raises:
            GitHubAPIError: On API errors
            ValueError: If issue_number is invalid
        """
        if issue_number < 1:
            raise ValueError(f"Invalid issue_number: {issue_number}. Must be positive.")

        endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        response = self._make_request(endpoint)

        if not isinstance(response, list):
            raise GitHubAPIError("Expected list response from comments endpoint")

        # Parse comments
        comments = []
        for item in response:
            try:
                comment = Comment.from_json(item)
                comments.append(comment)
            except (KeyError, TypeError, ValueError) as e:
                # Log parsing error but continue with other comments
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to parse comment from API response: {e}")
                continue

        return comments
