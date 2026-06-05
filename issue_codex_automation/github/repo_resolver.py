"""GitHub repository resolver - extract owner/repo from git remote."""

import re
import subprocess
from typing import Optional, Tuple

from ..errors import RepositoryError


def resolve_github_repo(owner_override: Optional[str] = None, repo_override: Optional[str] = None) -> Tuple[str, str]:
    """
    Resolve GitHub repository owner and name.

    If both overrides are provided, use them directly.
    Otherwise, extract from git remote.origin.url.

    Args:
        owner_override: Explicit repository owner (optional)
        repo_override: Explicit repository name (optional)

    Returns:
        Tuple of (owner, repo)

    Raises:
        RepositoryError: If git remote is not configured, not a GitHub URL,
                        or URL parsing fails
    """
    if owner_override and repo_override:
        return owner_override, repo_override

    # Run git config to get remote URL
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2
        )
        remote_url = result.stdout.strip()
    except subprocess.CalledProcessError:
        raise RepositoryError(
            "No git remote.origin.url configured. "
            "Ensure you're in a git repository with a GitHub remote, "
            "or provide GITHUB_OWNER and GITHUB_REPO explicitly."
        )
    except subprocess.TimeoutExpired:
        raise RepositoryError("Git command timed out while reading remote URL")
    except FileNotFoundError:
        raise RepositoryError("Git executable not found. Please ensure git is installed.")

    if not remote_url:
        raise RepositoryError("Git remote.origin.url is empty")

    # Parse GitHub URL
    owner, repo = _parse_github_url(remote_url)

    # Apply any partial overrides
    if owner_override:
        owner = owner_override
    if repo_override:
        repo = repo_override

    return owner, repo


def _parse_github_url(url: str) -> Tuple[str, str]:
    """
    Parse GitHub SSH or HTTPS URL to extract owner and repo.

    Supported formats:
    - SSH: git@github.com:owner/repo.git
    - HTTPS: https://github.com/owner/repo.git
    - HTTPS (no .git): https://github.com/owner/repo

    Args:
        url: Git remote URL

    Returns:
        Tuple of (owner, repo)

    Raises:
        RepositoryError: If URL is not a recognized GitHub format
    """
    # Strip whitespace
    url = url.strip()

    # SSH format: git@github.com:owner/repo.git
    ssh_pattern = r"git@github\.com:([^/]+)/(.+?)(?:\.git)?$"
    match = re.match(ssh_pattern, url)
    if match:
        owner, repo = match.groups()
        return owner, _strip_git_suffix(repo)

    # HTTPS format: https://github.com/owner/repo.git
    https_pattern = r"https://github\.com/([^/]+)/(.+?)(?:\.git)?$"
    match = re.match(https_pattern, url)
    if match:
        owner, repo = match.groups()
        return owner, _strip_git_suffix(repo)

    # Not a recognized GitHub URL
    raise RepositoryError(
        f"Remote URL is not a GitHub repository: {url}\n"
        f"Expected format: git@github.com:owner/repo.git or https://github.com/owner/repo.git"
    )


def _strip_git_suffix(repo: str) -> str:
    """
    Strip .git suffix from repository name if present.

    Args:
        repo: Repository name, possibly with .git suffix

    Returns:
        Repository name without .git suffix
    """
    if repo.endswith(".git"):
        return repo[:-4]
    return repo
