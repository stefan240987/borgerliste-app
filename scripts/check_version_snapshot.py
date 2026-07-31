#!/usr/bin/env python3
"""Tjek at APP_VERSION har et matchende git-tag (release-snapshot)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import APP_VERSION  # noqa: E402


def git_tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{tag}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def changelog_has_version(version: str) -> bool:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return f"## [{version}]" in changelog


def main() -> int:
    tag = f"v{APP_VERSION}"

    if not changelog_has_version(APP_VERSION):
        print(f"FEJL: CHANGELOG.md mangler sektion ## [{APP_VERSION}]", file=sys.stderr)
        return 1

    if not git_tag_exists(tag):
        print(
            f"FEJL: Ingen git-snapshot for {APP_VERSION} — kør ./scripts/release_snapshot.sh",
            file=sys.stderr,
        )
        return 1

    short = subprocess.check_output(
        ["git", "rev-parse", "--short", tag],
        cwd=ROOT,
        text=True,
    ).strip()
    print(f"OK — {tag} peger på {short}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
