#!/usr/bin/env python3
"""Udtræk GitHub Release-titel og -noter fra CHANGELOG.md for en given version."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_PATH = ROOT / "CHANGELOG.md"

SECTION_HEADER = re.compile(r"^## \[([^\]]+)\]", re.MULTILINE)
SUBTITLE = re.compile(r"^## \[[^\]]+\] — [^(]+\(([^)]+)\)")


def _load_sections() -> dict[str, str]:
    text = CHANGELOG_PATH.read_text(encoding="utf-8")
    matches = list(SECTION_HEADER.finditer(text))
    sections: dict[str, str] = {}

    for index, match in enumerate(matches):
        version = match.group(1)
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[version] = text[start:end].strip()

    return sections


def release_title(version: str) -> str:
    section = _load_sections().get(version)
    if not section:
        raise ValueError(f"CHANGELOG.md mangler sektion ## [{version}]")

    first_line = section.splitlines()[0]
    subtitle_match = SUBTITLE.match(first_line)
    if subtitle_match:
        return f"v{version} — {subtitle_match.group(1)}"
    return f"v{version}"


def release_body(version: str) -> str:
    section = _load_sections().get(version)
    if not section:
        raise ValueError(f"CHANGELOG.md mangler sektion ## [{version}]")

    lines = section.splitlines()
    body_lines = lines[1:]
    while body_lines and body_lines[-1].strip() == "---":
        body_lines.pop()
    return "\n".join(body_lines).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="APP_VERSION uden v-prefix (fx 1.4.1)")
    parser.add_argument(
        "--title",
        action="store_true",
        help="Skriv kun release-titel",
    )
    parser.add_argument(
        "--body",
        action="store_true",
        help="Skriv kun release-noter (markdown)",
    )
    args = parser.parse_args()

    try:
        if args.title:
            print(release_title(args.version))
        elif args.body:
            print(release_body(args.version))
        else:
            print(release_title(args.version))
            print()
            print(release_body(args.version))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
