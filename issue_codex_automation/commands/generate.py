"""Generate command: create goal prompt for an issue."""

import sys
from pathlib import Path
from typing import Optional, List

from ..config import Config
from ..github import GitHubClient, GitHubAPIError, Issue, Comment
from ..state import StateManager
from ..prompt import GoalPromptBuilder
from ..logger import get_logger
from ..errors import StateError

logger = get_logger(__name__)


class GenerateCommand:
    """Generate command implementation."""

    def __init__(self, config: Config):
        self.config = config
        self.github = GitHubClient(config.github_token)
        self.state = StateManager(config.state_dir)
        self.prompt_builder = GoalPromptBuilder()

    def execute(self, issue_number: int, force: bool = False, no_comments: bool = False) -> int:
        """
        Execute the generate command.

        Args:
            issue_number: GitHub issue number
            force: Overwrite existing goal.md if present
            no_comments: Skip fetching comments

        Returns:
            Exit code (0=success, 2=GitHub API error, 3=state error, 4=not eligible, 5=not in state)
        """
        try:
            # Check if issue is in state
            if not self._validate_issue_in_state(issue_number):
                return 5

            # Fetch and validate issue
            issue = self._fetch_and_validate_issue(issue_number)
            if issue is None:
                return 4

            # Fetch comments if needed
            comments = self._fetch_comments_if_needed(issue_number, no_comments)

            # Prepare run directory
            run_dir, goal_path = self._prepare_run_directory(issue_number, force)
            if run_dir is None:
                return 4

            # Generate and write outputs
            self._generate_and_write_goal(issue, comments, goal_path, run_dir)

            # Update state
            self.state.mark_generated(issue_number)
            self.state.save()

            # Print success message
            self._print_success(goal_path, run_dir)

            return 0

        except GitHubAPIError as e:
            print(f"GitHub API error: {e}", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            logger.debug("Full traceback:", exc_info=True)
            return 3

    def _validate_issue_in_state(self, issue_number: int) -> bool:
        """Check if issue exists in local state."""
        issue_key = str(issue_number)
        if issue_key not in self.state.state.discovered_issues:
            print(
                f"Issue #{issue_number} not found in local state. Run 'check' first.",
                file=sys.stderr,
            )
            return False
        return True

    def _fetch_and_validate_issue(self, issue_number: int) -> Optional[Issue]:
        """Fetch issue and validate eligibility."""
        logger.info(f"Fetching issue #{issue_number} from GitHub...")
        issue = self.github.get_issue(self.config.repo_owner, self.config.repo_name, issue_number)

        # Check eligibility
        if issue.is_pull_request:
            print(f"#{issue_number} is a pull request, not an issue.", file=sys.stderr)
            return None

        if self.config.label_filter not in issue.labels:
            print(
                f"Issue #{issue_number} does not have required label '{self.config.label_filter}'",
                file=sys.stderr,
            )
            return None

        return issue

    def _fetch_comments_if_needed(self, issue_number: int, no_comments: bool) -> List[Comment]:
        """Fetch issue comments if enabled."""
        comments = []
        if not no_comments and self.config.include_comments:
            logger.info("Fetching issue comments...")
            comments = self.github.get_issue_comments(self.config.repo_owner, self.config.repo_name, issue_number)
            logger.info(f"Fetched {len(comments)} comments")
        return comments

    def _prepare_run_directory(self, issue_number: int, force: bool) -> tuple[Optional[Path], Optional[Path]]:
        """Prepare run directory and check if goal already exists."""
        run_dir = self.config.state_dir / "runs" / f"issue-{issue_number}"

        # Validate run_dir is still under state_dir (defense in depth)
        run_dir = run_dir.resolve()
        try:
            run_dir.relative_to(self.config.state_dir.resolve())
        except ValueError:
            print(f"Security error: Invalid run directory path", file=sys.stderr)
            return None, None

        goal_path = run_dir / "goal.md"

        if goal_path.exists() and not force:
            print(
                f"Goal already exists: {goal_path}\n"
                f"Use --force to overwrite.",
                file=sys.stderr,
            )
            return None, None

        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir, goal_path

    def _generate_and_write_goal(self, issue: Issue, comments: List[Comment], goal_path: Path, run_dir: Path) -> None:
        """Generate goal prompt and write output files."""
        import json
        from datetime import datetime

        # Generate goal prompt
        logger.info("Generating goal prompt...")
        goal_content = self.prompt_builder.build(issue)

        # Write goal.md with error handling
        try:
            with open(goal_path, "w", encoding="utf-8") as f:
                f.write(goal_content)
        except OSError as e:
            raise StateError(f"Failed to write goal file: {e}")

        # Write metadata.json
        metadata = {
            "issue_number": issue.number,
            "issue_title": issue.title,
            "issue_url": issue.url,
            "labels": issue.labels,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            "author": issue.author,
            "comments_count": len(comments),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

        metadata_path = run_dir / "metadata.json"
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
                f.write("\n")  # Trailing newline
        except OSError as e:
            raise StateError(f"Failed to write metadata file: {e}")

    def _print_success(self, goal_path: Path, run_dir: Path) -> None:
        """Print success message with execution instructions."""
        metadata_path = run_dir / "metadata.json"
        print(f"\nGenerated goal prompt: {goal_path}")
        print(f"Metadata: {metadata_path}")
        print("\nTo execute with Codex, run:")
        print(f"  codex exec -C . - < {goal_path}")
