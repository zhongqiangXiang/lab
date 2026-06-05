"""State schema dataclasses for issue tracking and persistence.

This module defines the data structures used to track processed GitHub issues
and their workflow status in the local state file.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Literal, Optional

# Current schema version for state.json
STATE_SCHEMA_VERSION = "1.0.0"

# Issue status type definition
IssueStatus = Literal["new", "generated", "failed"]


@dataclass
class IssueRecord:
    """Tracks the processing status of a single GitHub issue.

    Attributes:
        discovered_at: ISO 8601 timestamp when the issue was first discovered
        status: Current workflow status (new/generated/failed)
    """

    discovered_at: str  # ISO 8601 format
    status: IssueStatus

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation with discovered_at and status fields
        """
        return {
            "discovered_at": self.discovered_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IssueRecord":
        """Deserialize from dictionary loaded from JSON.

        Args:
            data: Dictionary with discovered_at and status keys

        Returns:
            IssueRecord instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If status is not a valid IssueStatus value
        """
        status = data["status"]
        if status not in ("new", "generated", "failed"):
            raise ValueError(f"Invalid status: {status}")

        return cls(
            discovered_at=data["discovered_at"],
            status=status,
        )


@dataclass
class State:
    """Root state object persisted to state.json.

    Attributes:
        version: Schema version string (for future migration compatibility)
        last_seen_at: ISO 8601 timestamp of the last successful check command
        discovered_issues: Map of issue number (as string) to IssueRecord
    """

    version: str = STATE_SCHEMA_VERSION
    last_seen_at: str = ""  # ISO 8601 format, empty string if never run
    discovered_issues: Dict[str, IssueRecord] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage.

        Returns:
            Dictionary with version, last_seen_at, and discovered_issues
        """
        return {
            "version": self.version,
            "last_seen_at": self.last_seen_at,
            "discovered_issues": {
                issue_num: record.to_dict()
                for issue_num, record in self.discovered_issues.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "State":
        """Deserialize from dictionary loaded from JSON.

        Args:
            data: Dictionary with version, last_seen_at, and discovered_issues

        Returns:
            State instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If data format is invalid
        """
        # Handle version for future migration logic
        version = data.get("version", "1.0.0")
        last_seen_at = data.get("last_seen_at", "")

        discovered_issues = {}
        for issue_num, record_data in data.get("discovered_issues", {}).items():
            discovered_issues[issue_num] = IssueRecord.from_dict(record_data)

        return cls(
            version=version,
            last_seen_at=last_seen_at,
            discovered_issues=discovered_issues,
        )

    def get_issue_status(self, issue_number: int) -> Optional[IssueStatus]:
        """Get the status of a tracked issue.

        Args:
            issue_number: GitHub issue number

        Returns:
            IssueStatus if the issue is tracked, None otherwise
        """
        record = self.discovered_issues.get(str(issue_number))
        return record.status if record else None

    def add_or_update_issue(
        self,
        issue_number: int,
        status: IssueStatus,
        discovered_at: Optional[str] = None,
    ) -> None:
        """Add a new issue or update an existing one.

        Args:
            issue_number: GitHub issue number
            status: New status to set
            discovered_at: ISO 8601 timestamp (defaults to now if adding new issue)
        """
        issue_key = str(issue_number)

        if issue_key in self.discovered_issues:
            # Update existing record
            self.discovered_issues[issue_key].status = status
        else:
            # Add new record
            if discovered_at is None:
                discovered_at = datetime.utcnow().isoformat() + "Z"
            self.discovered_issues[issue_key] = IssueRecord(
                discovered_at=discovered_at,
                status=status,
            )

    def update_last_seen(self, timestamp: Optional[str] = None) -> None:
        """Update the last_seen_at timestamp.

        Args:
            timestamp: ISO 8601 timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat() + "Z"
        self.last_seen_at = timestamp
