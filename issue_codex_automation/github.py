"""GitHub API client."""

import json
import urllib.request
import urllib.error
import urllib.parse
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass

from .logger import get_logger

logger = get_logger(__name__)


class GitHubAPIError(Exception):
    """GitHub API error."""
    pass


@dataclass
class Issue:
    """GitHub issue representation."""
    number: int
    title: str
    body: str
    state: str
    labels: List[str]
    url: str
    author: str
    created_at: datetime
    updated_at: datetime
    is_pull_request: bool


@dataclass
class Comment:
    """GitHub issue comment representation."""
    id: int
    author: str
    body: str
    created_at: datetime


class GitHubClient:
    """GitHub REST API client."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, repo: str):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token
            repo: Repository in format 'owner/repo'
        """
        self.token = token
        self.repo = repo

    def fetch_issues(
        self,
        state: str = "open",
        labels: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        per_page: int = 100,
    ) -> List[Issue]:
        """
        Fetch issues from GitHub.

        Args:
            state: Issue state ('open', 'closed', 'all')
            labels: Optional list of labels to filter by
            since: Optional timestamp to filter issues updated after
            per_page: Results per page (max 100)

        Returns:
            List of Issue objects

        Raises:
            GitHubAPIError: If API request fails
        """
        url = f"{self.BASE_URL}/repos/{self.repo}/issues"
        params = {
            "state": state,
            "sort": "updated",
            "direction": "desc",
            "per_page": str(per_page),
        }

        if labels:
            params["labels"] = ",".join(labels)

        if since:
            params["since"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Use urllib.parse.urlencode for proper escaping
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"

        logger.debug(f"GET {url} (params redacted)")

        data = self._request(full_url)

        issues = []
        for item in data:
            issues.append(self._parse_issue(item))

        return issues

    def fetch_issue(self, issue_number: int) -> Issue:
        """
        Fetch a single issue by number.

        Args:
            issue_number: Issue number

        Returns:
            Issue object

        Raises:
            GitHubAPIError: If API request fails
        """
        url = f"{self.BASE_URL}/repos/{self.repo}/issues/{issue_number}"
        logger.debug(f"GET /repos/{self.repo}/issues/{issue_number}")

        data = self._request(url)
        return self._parse_issue(data)

    def fetch_issue_comments(self, issue_number: int) -> List[Comment]:
        """
        Fetch comments for an issue.

        Args:
            issue_number: Issue number

        Returns:
            List of Comment objects

        Raises:
            GitHubAPIError: If API request fails
        """
        url = f"{self.BASE_URL}/repos/{self.repo}/issues/{issue_number}/comments"
        logger.debug(f"GET /repos/{self.repo}/issues/{issue_number}/comments")

        data = self._request(url)

        comments = []
        for item in data:
            comments.append(Comment(
                id=item["id"],
                author=item["user"]["login"],
                body=item["body"] or "",
                created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
            ))

        return comments

    def _request(self, url: str) -> dict:
        """
        Make HTTP request to GitHub API.

        Args:
            url: Full URL to request

        Returns:
            Parsed JSON response

        Raises:
            GitHubAPIError: If request fails
        """
        # Validate URL scheme to prevent SSRF
        if not url.startswith("https://api.github.com/"):
            raise GitHubAPIError(f"Invalid URL scheme - only HTTPS to api.github.com is allowed")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            # Do not log error_body as it might contain sensitive info
            logger.debug(f"HTTP {e.code}: {e.reason}")

            if e.code == 401:
                raise GitHubAPIError("Authentication failed. Check GITHUB_TOKEN.")
            elif e.code == 403:
                raise GitHubAPIError("API rate limit exceeded or access forbidden.")
            elif e.code == 404:
                raise GitHubAPIError(f"Repository or resource not found: {self.repo}")
            else:
                raise GitHubAPIError(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise GitHubAPIError(f"Network error: {e.reason}")
        except Exception as e:
            raise GitHubAPIError(f"Unexpected error: {e}")

    def _parse_issue(self, data: dict) -> Issue:
        """Parse GitHub API issue response into Issue object."""
        return Issue(
            number=data["number"],
            title=data["title"],
            body=data.get("body") or "",
            state=data["state"],
            labels=[label["name"] for label in data.get("labels", [])],
            url=data["html_url"],
            author=data["user"]["login"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            is_pull_request="pull_request" in data,
        )
