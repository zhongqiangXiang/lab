#!/usr/bin/env python3
"""
CLI entry point for issue-codex-automation.

Provides two commands:
  check    - Discover eligible new issues and update local state
  generate - Generate goal prompt for a specific issue
"""

import argparse
import sys
import os
from pathlib import Path

from .commands.check import CheckCommand
from .commands.generate import GenerateCommand
from .config import load_config, ConfigError
from .logger import setup_logging

__version__ = "0.1.0"


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="issue-codex-automation",
        description="GitHub issue-driven Codex automation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to .env file (default: .env in current directory)",
    )

    parser.add_argument(
        "--state-dir",
        metavar="PATH",
        help="Override STATE_DIR (default: .codex_issue_agent)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # check command
    check_parser = subparsers.add_parser(
        "check",
        help="Discover eligible new issues and update local state",
    )
    check_parser.add_argument(
        "--since",
        metavar="TIMESTAMP",
        help="Optional ISO-8601 timestamp to override last_seen_at from state",
    )
    check_parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-fetch all open issues, ignore last_seen_at",
    )

    # generate command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate goal prompt for a specific issue",
    )
    generate_parser.add_argument(
        "issue_number",
        type=int,
        help="GitHub issue number",
    )
    generate_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing goal.md if present",
    )
    generate_parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Skip fetching issue comments (default: fetch if INCLUDE_COMMENTS=true)",
    )

    return parser


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Setup logging
    setup_logging(verbose=args.verbose)

    try:
        # Load configuration
        config_path = args.config if args.config else None
        config = load_config(config_path=config_path, state_dir_override=args.state_dir)

        # Dispatch to command
        if args.command == "check":
            cmd = CheckCommand(config)
            return cmd.execute(since=args.since, force_refresh=args.force_refresh)
        elif args.command == "generate":
            cmd = GenerateCommand(config)
            return cmd.execute(
                issue_number=args.issue_number,
                force=args.force,
                no_comments=args.no_comments,
            )
        else:
            parser.print_help()
            return 1

    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
