"""State management for tracking processed issues."""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .github import Issue
from .logger import get_logger

logger = get_logger(__name__)


class StateManager:
    """Manages local state file for issue tracking."""

    def __init__(self, state_dir: Path):
        """
        Initialize state manager.

        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = Path(state_dir).resolve()

        # Validate state_dir is under current working directory
        cwd = Path.cwd().resolve()
        try:
            self.state_dir.relative_to(cwd)
        except ValueError:
            raise ValueError(
                f"State directory must be within current working directory. "
                f"Got: {self.state_dir}, expected under: {cwd}"
            )

        self.state_file = self.state_dir / "state.json"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load state from disk."""
        if not self.state_file.exists():
            return {
                "last_seen_at": None,
                "issues": {},
            }

        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}. Starting fresh.")
            return {
                "last_seen_at": None,
                "issues": {},
            }

    def _save_state(self) -> None:
        """Save state to disk."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self._state, f, indent=2)
            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            raise

    def get_last_seen_at(self) -> Optional[datetime]:
        """Get the last_seen_at timestamp from state."""
        last_seen = self._state.get("last_seen_at")
        if last_seen:
            return datetime.fromisoformat(last_seen)
        return None

    def update_from_issues(self, issues: List[Issue]) -> None:
        """
        Update state from a list of fetched issues.

        Args:
            issues: List of Issue objects
        """
        if not issues:
            return

        # Update last_seen_at to the most recent updated_at
        most_recent = max(issue.updated_at for issue in issues)
        self._state["last_seen_at"] = most_recent.isoformat()

        # Add or update issues
        for issue in issues:
            issue_key = str(issue.number)
            if issue_key not in self._state["issues"]:
                self._state["issues"][issue_key] = {
                    "number": issue.number,
                    "title": issue.title,
                    "url": issue.url,
                    "labels": issue.labels,
                    "first_seen": datetime.now().isoformat(),
                    "last_seen": issue.updated_at.isoformat(),
                    "generated": False,
                }
                logger.info(f"New issue tracked: #{issue.number} - {issue.title}")
            else:
                # Update last_seen
                self._state["issues"][issue_key]["last_seen"] = issue.updated_at.isoformat()
                self._state["issues"][issue_key]["title"] = issue.title
                self._state["issues"][issue_key]["labels"] = issue.labels

        self._save_state()

    def has_issue(self, issue_number: int) -> bool:
        """Check if an issue is tracked in state."""
        return str(issue_number) in self._state["issues"]

    def mark_generated(self, issue_number: int) -> None:
        """Mark an issue as having a generated goal."""
        issue_key = str(issue_number)
        if issue_key in self._state["issues"]:
            self._state["issues"][issue_key]["generated"] = True
            self._state["issues"][issue_key]["generated_at"] = datetime.now().isoformat()
            self._save_state()
            logger.info(f"Marked issue #{issue_number} as generated")
