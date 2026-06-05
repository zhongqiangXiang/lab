"""Check command: discover eligible new issues."""

import sys
from typing import Optional, List
from datetime import datetime

from ..config import Config
from ..github import GitHubClient, GitHubAPIError
from ..state import StateManager
from ..logger import get_logger

logger = get_logger(__name__)


class CheckCommand:
    """Check command implementation."""

    def __init__(self, config: Config):
        self.config = config
        self.github = GitHubClient(config.github_token)
        self.state = StateManager(config.state_dir)

    def execute(self, since: Optional[str] = None, force_refresh: bool = False) -> int:
        """
        Execute the check command.

        Args:
            since: Optional ISO-8601 timestamp to override last_seen_at
            force_refresh: Re-fetch all open issues, ignore last_seen_at

        Returns:
            Exit code (0=success, 2=GitHub API error, 3=state error)
        """
        try:
            # Determine since timestamp
            if force_refresh:
                since_ts = None
                logger.info("Force refresh mode: fetching all open issues")
            elif since:
                since_ts = since
                logger.info(f"Using --since timestamp: {since_ts}")
            else:
                since_ts = self.state.get_last_seen()
                if since_ts:
                    logger.info(f"Using last_seen_at from state: {since_ts}")
                else:
                    logger.info("No last_seen_at in state; fetching all open issues")

            # Fetch issues from GitHub
            logger.info(f"Fetching open issues from {self.config.repo_full_name}...")
            issues = self.github.get_issues(
                owner=self.config.repo_owner,
                repo=self.config.repo_name,
                state="open",
                labels=self.config.label_filter,
                since=since_ts,
            )

            # Filter out PRs
            issues = [issue for issue in issues if not issue.is_pull_request]

            logger.info(f"Found {len(issues)} eligible issues")

            if not issues:
                print("No new eligible issues found.")
                # Update last_seen_at even if no new issues
                self.state.update_last_seen()
                self.state.save()
                return 0

            # Update state with discovered issues
            from datetime import datetime
            for issue in issues:
                self.state.add_issue(issue.number, status="new")

            # Update last_seen_at timestamp
            self.state.update_last_seen()
            self.state.save()

            # Print table
            self._print_table(issues)

            return 0

        except GitHubAPIError as e:
            print(f"GitHub API error: {e}", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"State file error: {e}", file=sys.stderr)
            return 3

    def _print_table(self, issues: List) -> None:
        """Print a table of issues."""
        print("\nNew eligible issues:")
        print("-" * 100)
        print(f"{'#':<8} {'Title':<50} {'Labels':<20} {'URL'}")
        print("-" * 100)

        for issue in issues:
            labels_str = ", ".join(issue.labels[:3])  # First 3 labels
            if len(issue.labels) > 3:
                labels_str += "..."

            title = issue.title[:47] + "..." if len(issue.title) > 50 else issue.title

            print(f"{issue.number:<8} {title:<50} {labels_str:<20} {issue.url}")

        print("-" * 100)
        print(f"Total: {len(issues)} issues")
