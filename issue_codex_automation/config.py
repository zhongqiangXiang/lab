"""Configuration loading and validation."""

import os
from pathlib import Path
from typing import Optional


class ConfigError(Exception):
    """Configuration validation error."""
    pass


class Config:
    """Configuration holder."""

    def __init__(
        self,
        github_token: str,
        repo_owner: str,
        repo_name: str,
        state_dir: Path,
        label_filter: str = "codex-ready",
        include_comments: bool = False,
    ):
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.state_dir = state_dir
        self.label_filter = label_filter
        self.include_comments = include_comments

    @property
    def repo_full_name(self) -> str:
        """Return owner/repo."""
        return f"{self.repo_owner}/{self.repo_name}"


def load_config(config_path: Optional[str] = None, state_dir_override: Optional[str] = None) -> Config:
    """
    Load configuration from environment or .env file.

    Args:
        config_path: Optional path to .env file
        state_dir_override: Optional STATE_DIR override from CLI

    Returns:
        Config object

    Raises:
        ConfigError: If required configuration is missing or invalid
    """
    # Load .env if specified
    if config_path:
        env_path = Path(config_path)
        if not env_path.exists():
            raise ConfigError(f".env file not found: {config_path}")
        _load_env_file(env_path)
    elif Path(".env").exists():
        _load_env_file(Path(".env"))

    # Validate GITHUB_TOKEN
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not github_token:
        raise ConfigError(
            "GITHUB_TOKEN is required. Set it in environment or .env file."
        )

    # Validate token format (should start with ghp_, gho_, ghs_, or github_pat_)
    if not any(github_token.startswith(prefix) for prefix in ["ghp_", "gho_", "ghs_", "github_pat_"]):
        raise ConfigError(
            "GITHUB_TOKEN appears to be invalid (expected format: ghp_*, gho_*, ghs_*, or github_pat_*)"
        )

    # Resolve repository
    repo_owner, repo_name = _resolve_repository()

    # Resolve state directory
    if state_dir_override:
        state_dir = Path(state_dir_override)
    else:
        state_dir = Path(os.environ.get("STATE_DIR", ".codex_issue_agent"))

    # Validate state_dir to prevent path traversal
    state_dir = state_dir.resolve()
    cwd = Path.cwd().resolve()
    try:
        state_dir.relative_to(cwd)
    except ValueError:
        raise ConfigError(
            f"STATE_DIR must be within the current working directory. "
            f"Got: {state_dir}, expected under: {cwd}"
        )

    # Ensure state directory exists
    state_dir.mkdir(parents=True, exist_ok=True)

    # Optional configuration
    label_filter = os.environ.get("LABEL_FILTER", "codex-ready").strip()
    include_comments = os.environ.get("INCLUDE_COMMENTS", "false").lower() in ("true", "1", "yes")

    return Config(
        github_token=github_token,
        repo_owner=repo_owner,
        repo_name=repo_name,
        state_dir=state_dir,
        label_filter=label_filter,
        include_comments=include_comments,
    )


def _load_env_file(path: Path) -> None:
    """Load environment variables from .env file.

    Args:
        path: Path to .env file

    Raises:
        ConfigError: If .env file contains invalid content
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")

                    # Validate key is a valid environment variable name
                    if not key.isidentifier():
                        raise ConfigError(
                            f"Invalid environment variable name in .env at line {line_num}: {key}"
                        )

                    # Check for null bytes or other dangerous characters in values
                    if '\0' in value:
                        raise ConfigError(
                            f"Invalid character in .env value at line {line_num}"
                        )

                    os.environ[key] = value
    except OSError as e:
        raise ConfigError(f"Failed to read .env file: {e}")


def _resolve_repository() -> tuple[str, str]:
    """
    Resolve repository owner and name from git remote or environment.

    Returns:
        Tuple of (owner, name)

    Raises:
        ConfigError: If repository cannot be resolved
    """
    # Check environment override first
    repo_override = os.environ.get("GITHUB_REPO", "").strip()
    if repo_override:
        return _parse_repo_from_env(repo_override)

    # Try to detect from git remote
    return _parse_repo_from_git()


def _parse_repo_from_env(repo_override: str) -> tuple[str, str]:
    """Parse repository from GITHUB_REPO environment variable."""
    if "/" not in repo_override:
        raise ConfigError(
            f"GITHUB_REPO must be in format 'owner/repo', got: {repo_override}"
        )
    owner, name = repo_override.split("/", 1)
    # Validate owner and name contain only safe characters
    if not _is_safe_repo_component(owner) or not _is_safe_repo_component(name):
        raise ConfigError(
            f"GITHUB_REPO contains invalid characters. Use alphanumeric, dash, underscore, and dot only."
        )
    return owner.strip(), name.strip()


def _parse_repo_from_git() -> tuple[str, str]:
    """Parse repository from git remote URL."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        remote_url = result.stdout.strip()

        if "github.com" not in remote_url:
            raise ConfigError(
                f"Git remote origin is not a GitHub URL: {remote_url}. "
                "Set GITHUB_REPO environment variable instead."
            )

        return _parse_github_url(remote_url)

    except subprocess.TimeoutExpired:
        raise ConfigError(
            "Git command timed out. "
            "Set GITHUB_REPO environment variable (format: owner/repo)."
        )
    except subprocess.CalledProcessError:
        raise ConfigError(
            "Could not detect repository from git remote. "
            "Set GITHUB_REPO environment variable (format: owner/repo)."
        )
    except FileNotFoundError:
        raise ConfigError(
            "git command not found. "
            "Set GITHUB_REPO environment variable (format: owner/repo)."
        )


def _parse_github_url(remote_url: str) -> tuple[str, str]:
    """Parse owner/repo from a GitHub URL."""
    # Handle both SSH and HTTPS formats
    if remote_url.startswith("git@github.com:"):
        # SSH: git@github.com:owner/repo.git
        path = remote_url.split(":", 1)[1]
    elif "github.com/" in remote_url:
        # HTTPS: https://github.com/owner/repo.git
        path = remote_url.split("github.com/", 1)[1]
    else:
        raise ConfigError(f"Could not parse GitHub URL: {remote_url}")

    # Remove .git suffix
    if path.endswith(".git"):
        path = path[:-4]

    if "/" not in path:
        raise ConfigError(f"Could not parse owner/repo from: {path}")

    owner, name = path.split("/", 1)
    # Validate parsed components
    if not _is_safe_repo_component(owner) or not _is_safe_repo_component(name):
        raise ConfigError(
            f"Parsed repository path contains invalid characters: {path}"
        )
    return owner.strip(), name.strip()


def _is_safe_repo_component(component: str) -> bool:
    """
    Validate that a repository owner or name contains only safe characters.

    Args:
        component: Owner or repo name

    Returns:
        True if safe, False otherwise
    """
    import re
    # GitHub allows alphanumeric, dash, underscore, and dot
    return bool(re.match(r'^[a-zA-Z0-9._-]+$', component))
