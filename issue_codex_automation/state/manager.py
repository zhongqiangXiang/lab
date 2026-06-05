"""StateManager for reading and writing persistent issue tracking state.

This module provides atomic file operations for state.json persistence,
including schema validation, migration support, and convenience methods
for tracking issue workflow status.
"""

import json
import os
from pathlib import Path
from typing import List, Union, Optional

from .models import State, IssueStatus, STATE_SCHEMA_VERSION
from ..errors import StateError


class StateManager:
    """Manages persistent state for GitHub issue tracking.

    The StateManager handles loading, saving, and querying state.json which tracks:
    - Discovered issues and their workflow status
    - Last seen timestamp for incremental polling
    - Schema version for future migrations

    All file writes use atomic rename to prevent partial writes or corruption.

    Attributes:
        state_dir: Path to .codex_issue_agent directory
        state_file: Path to state.json file
        state: Current in-memory State object
    """

    def __init__(self, state_dir: Union[Path, str] = ".codex_issue_agent"):
        """Initialize StateManager with the given state directory.

        Args:
            state_dir: Directory path for state persistence (default: .codex_issue_agent)
                      Created if it doesn't exist.
        """
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "state.json"
        self.state = self._load()

    def _load(self) -> State:
        """Load state from state.json or create default if missing.

        Returns:
            State object loaded from disk or default empty state

        Raises:
            StateError: If state file exists but is invalid/corrupted
        """
        if not self.state_file.exists():
            # Return default state if file doesn't exist yet
            return State()

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate schema version and migrate if needed
            version = data.get("version", "1.0.0")
            if version != STATE_SCHEMA_VERSION:
                data = self._migrate_schema(data, version)

            return State.from_dict(data)

        except json.JSONDecodeError as e:
            raise StateError(f"State file is not valid JSON: {e}") from e
        except (KeyError, ValueError) as e:
            raise StateError(f"State file has invalid schema: {e}") from e
        except OSError as e:
            raise StateError(f"Failed to read state file: {e}") from e

    def _migrate_schema(self, data: dict, from_version: str) -> dict:
        """Migrate state data from an older schema version.

        Args:
            data: Raw state dictionary loaded from JSON
            from_version: Version string of the loaded data

        Returns:
            Migrated data dictionary compatible with current schema

        Note:
            Currently no migrations exist. This is a placeholder for future
            schema evolution. Unknown versions pass through unchanged.
        """
        # Future migration logic goes here
        # For now, just update version field
        data["version"] = STATE_SCHEMA_VERSION
        return data

    def save(self) -> None:
        """Save current state to disk atomically.

        Uses a temporary file + rename pattern to ensure atomic writes.
        Creates the state directory if it doesn't exist.

        Raises:
            StateError: If file write or rename fails
        """
        # Ensure state directory exists
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StateError(f"Failed to create state directory: {e}") from e

        # Write to temporary file first
        temp_file = self.state_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, indent=2)
                f.write("\n")  # Trailing newline for POSIX compliance

            # Atomic rename
            temp_file.replace(self.state_file)

        except OSError as e:
            # Clean up temp file on failure
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            raise StateError(f"Failed to save state file: {e}") from e

    def get_new_issues(self) -> List[int]:
        """Get list of issue numbers with status 'new'.

        Returns:
            List of issue numbers (as integers) that have status 'new',
            sorted in ascending order
        """
        new_issues = [
            int(issue_num)
            for issue_num, record in self.state.discovered_issues.items()
            if record.status == "new"
        ]
        return sorted(new_issues)

    def mark_generated(self, issue_number: int) -> None:
        """Mark an issue as having a generated goal prompt.

        Args:
            issue_number: GitHub issue number

        Raises:
            StateError: If the issue is not tracked in state
        """
        issue_key = str(issue_number)
        if issue_key not in self.state.discovered_issues:
            raise StateError(f"Issue #{issue_number} is not tracked in state")

        self.state.discovered_issues[issue_key].status = "generated"

    def mark_failed(self, issue_number: int) -> None:
        """Mark an issue as failed during processing.

        Args:
            issue_number: GitHub issue number

        Raises:
            StateError: If the issue is not tracked in state
        """
        issue_key = str(issue_number)
        if issue_key not in self.state.discovered_issues:
            raise StateError(f"Issue #{issue_number} is not tracked in state")

        self.state.discovered_issues[issue_key].status = "failed"

    def is_processed(self, issue_number: int) -> bool:
        """Check if an issue has already been processed.

        Args:
            issue_number: GitHub issue number

        Returns:
            True if issue status is 'generated' or 'failed', False otherwise
        """
        status = self.state.get_issue_status(issue_number)
        return status in ("generated", "failed")

    def add_issue(self, issue_number: int, status: IssueStatus = "new") -> None:
        """Add a newly discovered issue to state.

        If the issue already exists, this is a no-op (does not change status).

        Args:
            issue_number: GitHub issue number
            status: Initial status (default: 'new')
        """
        issue_key = str(issue_number)
        if issue_key not in self.state.discovered_issues:
            self.state.add_or_update_issue(issue_number, status)

    def update_last_seen(self, timestamp: Optional[str] = None) -> None:
        """Update the last_seen_at timestamp for incremental polling.

        Args:
            timestamp: ISO 8601 timestamp string (defaults to current UTC time)
        """
        self.state.update_last_seen(timestamp)

    def get_last_seen(self) -> str:
        """Get the last_seen_at timestamp.

        Returns:
            ISO 8601 timestamp string, or empty string if never run
        """
        return self.state.last_seen_at
