"""Setup configuration for issue-codex-automation."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="issue-codex-automation",
    version="0.1.0",
    description="GitHub issue-driven Codex automation tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/issue-codex-automation",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        # No external dependencies for MVP; uses stdlib only
    ],
    entry_points={
        "console_scripts": [
            "issue-codex-automation=issue_codex_automation.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
