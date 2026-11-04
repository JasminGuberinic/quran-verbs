"""Publish build/pages to GitHub Pages: one fresh commit on an orphan gh-pages branch.

The commit is made in a throwaway repository whose work tree is build/pages, then
force-pushed: the branch always holds exactly one commit (the site as built), so audio
never piles up in history, and the project's own branches and working copy are never
touched. The plan is pure (`publish_commands`) so it is tested without git or a network.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

BRANCH = "gh-pages"
# The whole site goes up in one push (~200 MB of audio); git's default HTTP buffer makes
# GitHub refuse a push that large with "HTTP 400".
_PUSH_BUFFER = 1024 * 1024 * 1024


@dataclass(frozen=True)
class Identity:
    name: str
    email: str


def publish_commands(site: Path, git_dir: Path, remote: str, author: Identity, message: str) -> list[list[str]]:
    git = ["git", f"--git-dir={git_dir}", f"--work-tree={site}",
           "-c", f"user.name={author.name}", "-c", f"user.email={author.email}"]
    return [
        [*git, "init", "--quiet", f"--initial-branch={BRANCH}"],
        [*git, "add", "--all"],
        [*git, "commit", "--quiet", "--message", message],
        [*git, "-c", f"http.postBuffer={_PUSH_BUFFER}", "push", "--force", "--quiet", remote, f"{BRANCH}:{BRANCH}"],
    ]


def publish(site: Path, repository: Path, message: str) -> None:
    if not (site / "index.html").exists():
        raise FileNotFoundError(f"{site} holds no built site — run `fil pages` first")
    remote = _git(repository, "remote", "get-url", "origin")
    author = Identity(_git(repository, "config", "user.name"), _git(repository, "config", "user.email"))
    with tempfile.TemporaryDirectory() as folder:
        for command in publish_commands(site, Path(folder) / "repo.git", remote, author, message):
            subprocess.run(command, check=True)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", str(repository), *arguments],
                          check=True, capture_output=True, text=True).stdout.strip()
