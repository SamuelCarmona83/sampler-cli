#!/usr/bin/env python3
"""Bump release version for sampler-cli.

Updates the canonical sources (pyproject.toml + __init__.py) and all
"current version" mentions in docs + stamps the top CHANGELOG header.

Usage examples:
  python scripts/bump_version.py --patch
  python scripts/bump_version.py --minor
  python scripts/bump_version.py --major
  python scripts/bump_version.py 0.5.0
  python scripts/bump_version.py 0.4.3 --dry-run

After run:
  - Review changes
  - `uv lock` (updates lockfile project version)
  - pytest, clean dist/, build, tag vX.Y.Z, push

This is intentionally minimal (stdlib only, no external deps).
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_current_version() -> str:
    """Read version from pyproject.toml (single source of truth for build)."""
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        raise FileNotFoundError("pyproject.toml not found. Run from repo root.")
    text = pyproject.read_text(encoding="utf-8")
    m = re.search(r'^version = "(\d+\.\d+\.\d+)"', text, re.MULTILINE)
    if not m:
        raise RuntimeError("Could not parse version = \"X.Y.Z\" from pyproject.toml")
    return m.group(1)


def validate_version(ver: str) -> tuple[int, int, int]:
    parts = ver.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Invalid semver: {ver}. Expected X.Y.Z")
    return tuple(map(int, parts))  # type: ignore[return-value]


def bump_semver(current: str, level: str) -> str:
    major, minor, patch = validate_version(current)
    if level == "major":
        major += 1
        minor = patch = 0
    elif level == "minor":
        minor += 1
        patch = 0
    elif level == "patch":
        patch += 1
    else:
        raise ValueError(level)
    return f"{major}.{minor}.{patch}"


def update_file_version_line(path: Path, new_ver: str, dry: bool) -> bool:
    """Update version = "..." or __version__ = "..." line exactly (targeted & safe)."""
    if not path.exists():
        print(f"  skip (not found): {path}")
        return False
    text = path.read_text(encoding="utf-8")
    # Handle both "version = " (pyproject) and "__version__ = " (__init__)
    pattern = r'^(?P<prefix>(version|__version__) = ")(\d+\.\d+\.\d+)(")'
    new_text, n = re.subn(
        pattern,
        rf"\g<prefix>{new_ver}\g<4>",
        text,
        flags=re.MULTILINE,
    )
    if n == 0:
        print(f"  no version line matched in {path}")
        return False
    if dry:
        print(f"  [dry] would write {new_ver} -> {path}")
        return True
    path.write_text(new_text, encoding="utf-8")
    print(f"  updated {path} -> {new_ver}")
    return True


def replace_all_occurrences(path: Path, old: str, new: str, dry: bool, label: Optional[str] = None) -> int:
    """Simple string replace for docs (these files only contain the project version number)."""
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    if old not in text and f"v{old}" not in text:
        return 0
    # Replace bare version and v-prefixed (for tags)
    new_text = text.replace(old, new)
    new_text = new_text.replace(f"v{old}", f"v{new}")
    count = text.count(old) + text.count(f"v{old}")
    if dry:
        print(f"  [dry] {label or path.name}: {count} replacement(s) {old} -> {new}")
        return count
    path.write_text(new_text, encoding="utf-8")
    print(f"  updated {label or path.name}: {count} occurrence(s)")
    return count


def stamp_changelog_header(new_ver: str, today: str, dry: bool) -> bool:
    """Rewrite the topmost ## [X.Y.Z] - YYYY-MM-DD header to use new_ver + today."""
    path = Path("CHANGELOG.md")
    if not path.exists():
        print("  skip CHANGELOG.md (not found)")
        return False
    text = path.read_text(encoding="utf-8")
    # First header line
    m = re.search(r"^(## \[\d+\.\d+\.\d+\] - \d{4}-\d{2}-\d{2})", text, re.MULTILINE)
    if not m:
        print("  no ## [ver] header found at top of CHANGELOG.md")
        return False
    old_header = m.group(1)
    new_header = f"## [{new_ver}] - {today}"
    if old_header == new_header:
        print(f"  CHANGELOG.md header already {new_header}")
        return False
    new_text = text.replace(old_header, new_header, 1)
    if dry:
        print(f"  [dry] CHANGELOG.md: {old_header} -> {new_header}")
        return True
    path.write_text(new_text, encoding="utf-8")
    print(f"  CHANGELOG.md: {old_header} -> {new_header}")
    return True


def update_release_date(today: str, dry: bool) -> None:
    """Update the 'Current status (as of YYYY-MM-DD)' line in RELEASE.md."""
    path = Path("RELEASE.md")
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    new_text, n = re.subn(
        r"(Current status \(as of )\d{4}-\d{2}-\d{2}(\))",
        rf"\g<1>{today}\g<2>",
        text,
    )
    if n == 0:
        return
    if dry:
        print(f"  [dry] RELEASE.md: updated status date -> {today}")
        return
    path.write_text(new_text, encoding="utf-8")
    print(f"  RELEASE.md: status date -> {today}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bump release version (updates pyproject, __init__, docs, stamps changelog)."
    )
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--major", action="store_true", help="Bump X in X.Y.Z")
    g.add_argument("--minor", action="store_true", help="Bump Y in X.Y.Z")
    g.add_argument("--patch", action="store_true", help="Bump Z in X.Y.Z (typical for most releases)")
    g.add_argument("explicit_version", nargs="?", metavar="VERSION", help="Set exact version e.g. 0.5.0")

    parser.add_argument("-n", "--dry-run", action="store_true", help="Preview changes, do not write")
    parser.add_argument("--no-date", action="store_true", help="Do not touch dates in docs/CHANGELOG")
    args = parser.parse_args()

    try:
        current = get_current_version()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Current version: {current}")

    if args.explicit_version:
        new_ver = args.explicit_version
        validate_version(new_ver)
    else:
        level = "patch" if args.patch else ("minor" if args.minor else "major")
        new_ver = bump_semver(current, level)

    print(f"Target version:  {new_ver}")

    if new_ver == current:
        print("Already at target version. Nothing to do.")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    if not args.no_date:
        print(f"Date stamp:      {today}")
    else:
        today = "YYYY-MM-DD"  # placeholder if --no-date

    dry = args.dry_run
    if dry:
        print("--- DRY RUN (no files modified) ---\n")

    updated = []

    # 1. Canonical sources (precise line update)
    if update_file_version_line(Path("pyproject.toml"), new_ver, dry):
        updated.append("pyproject.toml")
    if update_file_version_line(Path("src/sampler/__init__.py"), new_ver, dry):
        updated.append("src/sampler/__init__.py")

    # 2. Human-facing docs (safe global replace of the number)
    if replace_all_occurrences(Path("README.md"), current, new_ver, dry):
        updated.append("README.md")
    if replace_all_occurrences(Path("TODO.md"), current, new_ver, dry):
        updated.append("TODO.md")
    if replace_all_occurrences(Path("RELEASE.md"), current, new_ver, dry, label="RELEASE.md"):
        updated.append("RELEASE.md")

    # 3. CHANGELOG top header (version + date)
    if stamp_changelog_header(new_ver, today, dry):
        updated.append("CHANGELOG.md")

    # 4. RELEASE status date
    if not args.no_date:
        update_release_date(today, dry)

    print()
    if dry:
        print("Dry run complete. Re-run without -n/--dry-run to apply.")
        return

    if updated:
        print("Files touched:", ", ".join(updated))
    else:
        print("No files needed changes.")

    print("\nRecommended follow-up:")
    print("  uv lock                 # refresh project version inside uv.lock")
    print("  pytest -q")
    print("  rm -rf dist build src/sampler_cli.egg-info  # per RELEASE.md checklist")
    print("  python -m build")
    print(f"  git commit -am 'chore(release): v{new_ver}' && git tag v{new_ver}")
    print("  git push && git push --tags")
    print("  # GitHub Release will trigger .github/workflows/publish.yml (trusted publishing)")


if __name__ == "__main__":
    main()
