"""Goal prompt builder using 5-section structure.

Transforms GitHub issues into audit-friendly goal prompts for Codex.
"""

import html
import re
from pathlib import Path
from typing import Optional

from ..github.models import Issue
from .templates import build_full_prompt, DEFAULT_DONE_CRITERIA, DEFAULT_REPOSITORY_RULES


class GoalPromptBuilder:
    """Builder for generating goal prompts from GitHub issues.

    Uses 5-section structure:
    - Objective: Derived from issue title and body
    - Scope: Issue URL and relevant repository context
    - Constraints: Quoted issue body, repository rules
    - Done when: Completion criteria
    - Stop if: Safety conditions
    """

    def __init__(
        self,
        agents_md_path: Optional[Path] = None,
        token_budget: Optional[int] = None,
    ):
        """Initialize the prompt builder.

        Args:
            agents_md_path: Path to AGENTS.md for repository context
            token_budget: Optional token budget estimate
        """
        self.agents_md_path = agents_md_path
        self.token_budget = token_budget

    def build(self, issue: Issue, repo_context: Optional[str] = None) -> str:
        """Build a goal prompt from a GitHub issue.

        Args:
            issue: GitHub issue data
            repo_context: Optional additional repository context

        Returns:
            Complete goal prompt text

        Raises:
            ValueError: If issue data is invalid or insufficient
        """
        # Validate issue
        if not issue.title or not issue.title.strip():
            raise ValueError(f"Issue #{issue.number} has empty title")

        # Sanitize issue body to prevent prompt injection
        sanitized_body = self._sanitize_issue_body(issue.body)

        # Derive objective from title and body
        objective = self._derive_objective(issue.title, sanitized_body)

        # Build scope details
        scope_details = self._build_scope_details(repo_context)

        # Get repository rules
        repository_rules = self._get_repository_rules()

        # Build token budget string
        token_budget_str = ""
        if self.token_budget:
            token_budget_str = f"Target: {self.token_budget:,} tokens"

        return build_full_prompt(
            objective=objective,
            issue_url=issue.url,
            issue_body=sanitized_body,
            scope_details=scope_details,
            repository_rules=repository_rules,
            done_criteria=DEFAULT_DONE_CRITERIA,
            token_budget=token_budget_str,
        )

    def _sanitize_issue_body(self, body: str) -> str:
        """Sanitize issue body to prevent prompt injection.

        Escapes markdown code blocks, HTML entities, and suspicious patterns
        that could be interpreted as AI instructions.

        Args:
            body: Raw issue body text

        Returns:
            Sanitized body text
        """
        if not body:
            return ""

        # HTML escape to prevent injection via HTML entities (escape quotes too)
        sanitized = html.escape(body, quote=True)

        # Escape triple backticks that could break out of markdown quoting
        sanitized = sanitized.replace("```", "\\`\\`\\`")

        # Flag suspicious instruction patterns (but don't remove them)
        # This helps human reviewers spot potential injection attempts
        instruction_patterns = [
            r"(?i)ignore\s+(previous|above|prior)\s+(instructions?|prompts?)",
            r"(?i)you\s+are\s+(now|actually)\s+",
            r"(?i)new\s+(instructions?|system\s+prompt)",
            r"(?i)disregard\s+(everything|all)",
        ]

        for pattern in instruction_patterns:
            if re.search(pattern, sanitized):
                # Prepend warning comment to the body
                sanitized = (
                    "[WARNING: Issue body contains text that resembles AI instructions]\n\n"
                    + sanitized
                )
                break

        return sanitized

    def _derive_objective(self, title: str, body: str) -> str:
        """Derive clear objective statement from issue title and body.

        Args:
            title: Issue title
            body: Sanitized issue body

        Returns:
            Objective statement
        """
        # Start with title
        objective = title.strip()

        # Extract first paragraph from body as additional context if helpful
        if body:
            lines = body.strip().split("\n")
            first_para = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    break
                # Skip markdown headers and horizontal rules
                if stripped.startswith("#") or stripped.startswith("---"):
                    continue
                first_para.append(stripped)

            if first_para:
                first_para_text = " ".join(first_para)
                # Only include if it adds meaningful context (not just title repetition)
                if len(first_para_text) > 20 and first_para_text.lower() != title.lower():
                    objective += f"\n\n{first_para_text[:200]}"
                    if len(first_para_text) > 200:
                        objective += "..."

        return objective

    def _build_scope_details(self, repo_context: Optional[str]) -> str:
        """Build scope details section.

        Args:
            repo_context: Optional repository context

        Returns:
            Scope details text
        """
        parts = []

        # Include AGENTS.md excerpt if available
        if self.agents_md_path and self.agents_md_path.exists():
            try:
                agents_content = self.agents_md_path.read_text(encoding="utf-8")
                # Extract relevant sections (skip long boilerplate)
                relevant_lines = []
                for line in agents_content.split("\n"):
                    # Include headers and non-Trellis content
                    if line.strip() and not line.startswith("<!--"):
                        relevant_lines.append(line)
                    # Stop at Trellis managed section end
                    if "TRELLIS:END" in line:
                        break

                if relevant_lines:
                    excerpt = "\n".join(relevant_lines[:30])  # Limit to first 30 lines
                    parts.append(f"**Repository Context (AGENTS.md excerpt):**\n\n{excerpt}")
            except Exception:
                # Silently skip if AGENTS.md cannot be read
                pass

        # Include additional repo context
        if repo_context:
            parts.append(f"**Additional Context:**\n\n{repo_context}")

        return "\n\n".join(parts) if parts else "No additional scope context available."

    def _get_repository_rules(self) -> str:
        """Get repository-specific rules and constraints.

        Returns:
            Repository rules text
        """
        # Use default rules for now
        # Future: parse from .codex/rules.md or similar
        return DEFAULT_REPOSITORY_RULES
