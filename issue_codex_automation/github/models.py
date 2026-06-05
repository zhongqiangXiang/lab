"""GitHub API data models.

Dataclasses for Issue and Comment with from_json parsing methods.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Issue:
    """GitHub issue representation.

    Attributes:
        number: Issue number (unique within repository)
        title: Issue title
        body: Issue description body text
        labels: List of label names
        url: GitHub HTML URL for the issue
        author: GitHub username of issue creator
        created_at: ISO8601 timestamp when issue was created
        updated_at: ISO8601 timestamp when issue was last updated
        is_pull_request: True if this is a pull request (has pull_request key)
    """

    number: int
    title: str
    body: str
    labels: List[str]
    url: str
    author: str
    created_at: str
    updated_at: str
    is_pull_request: bool

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Issue":
        """Parse Issue from GitHub API JSON response.

        Args:
            data: JSON response dict from GitHub Issues API

        Returns:
            Issue instance

        Raises:
            KeyError: If required fields are missing
            TypeError: If field types are incorrect
        """
        # Validate required fields
        required_fields = ["number", "title", "html_url", "user", "created_at", "updated_at"]
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise KeyError(f"Missing required fields: {', '.join(missing)}")

        # Extract nested user field
        if not isinstance(data["user"], dict) or "login" not in data["user"]:
            raise KeyError("Missing or invalid 'user.login' field")

        # Extract labels
        labels = []
        if "labels" in data and isinstance(data["labels"], list):
            labels = [
                label["name"] if isinstance(label, dict) and "name" in label else str(label)
                for label in data["labels"]
            ]

        return cls(
            number=int(data["number"]),
            title=str(data["title"]),
            body=str(data.get("body") or ""),
            labels=labels,
            url=str(data["html_url"]),
            author=str(data["user"]["login"]),
            created_at=str(data["created_at"]),
            updated_at=str(data["updated_at"]),
            is_pull_request="pull_request" in data,
        )


@dataclass
class Comment:
    """GitHub issue comment representation.

    Attributes:
        id: Unique comment ID
        body: Comment text content
        author: GitHub username of comment author
        created_at: ISO8601 timestamp when comment was created
    """

    id: int
    body: str
    author: str
    created_at: str

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Comment":
        """Parse Comment from GitHub API JSON response.

        Args:
            data: JSON response dict from GitHub Comments API

        Returns:
            Comment instance

        Raises:
            KeyError: If required fields are missing
            TypeError: If field types are incorrect
        """
        # Validate required fields
        required_fields = ["id", "body", "user", "created_at"]
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise KeyError(f"Missing required fields: {', '.join(missing)}")

        # Extract nested user field
        if not isinstance(data["user"], dict) or "login" not in data["user"]:
            raise KeyError("Missing or invalid 'user.login' field")

        return cls(
            id=int(data["id"]),
            body=str(data["body"]),
            author=str(data["user"]["login"]),
            created_at=str(data["created_at"]),
        )
