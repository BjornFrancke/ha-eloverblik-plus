#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "custom_components" / "eloverblik_plus" / "manifest.json"
PYPROJECT_PATH = ROOT / "pyproject.toml"
VENV_BIN_PATH = ROOT / "venv" / "bin"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
PYELOVERBLIK_REQUIREMENT = (
    "pyeloverblik @ git+https://github.com/BjornFrancke/ha-eloverblik-plus.git@{tag}"
)


def run_command(
    command: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def resolve_tool_command(tool: str, *, module: str) -> list[str]:
    executable = shutil.which(tool)
    if executable is not None:
        return [executable]

    venv_executable = VENV_BIN_PATH / tool
    if venv_executable.exists():
        return [str(venv_executable)]

    if importlib.util.find_spec(module) is not None:
        return [sys.executable, "-m", module]

    raise SystemExit(
        f"Could not find {tool}. Install dev dependencies or activate the project "
        "virtual environment before releasing."
    )


def require_clean_git_tree() -> None:
    result = run_command(["git", "status", "--porcelain"])
    if result.stdout.strip():
        print(
            "Git working tree must be clean before creating a release.", file=sys.stderr
        )
        print(result.stdout.rstrip(), file=sys.stderr)
        raise SystemExit(1)


def require_tag_absent(tag_name: str) -> None:
    result = run_command(["git", "tag", "--list", tag_name])
    if result.stdout.strip():
        print(f"Tag {tag_name} already exists.", file=sys.stderr)
        raise SystemExit(1)


def read_manifest_version() -> str:
    try:
        manifest_data = json.loads(MANIFEST_PATH.read_text())
    except json.JSONDecodeError as err:
        raise SystemExit(f"Manifest is not valid JSON: {err}") from err

    manifest_version = manifest_data.get("version")
    if not isinstance(manifest_version, str):
        raise SystemExit("Could not find manifest version.")

    return manifest_version


def build_requirement(tag_name: str) -> str:
    return PYELOVERBLIK_REQUIREMENT.format(tag=tag_name)


def read_pyproject_version() -> str:
    pyproject_content = PYPROJECT_PATH.read_text()
    pyproject_match = re.search(
        r'^version\s*=\s*"([^"]+)"', pyproject_content, re.MULTILINE
    )
    if pyproject_match is None:
        raise SystemExit("Could not find pyproject version.")

    return pyproject_match.group(1)


def read_current_version() -> str:
    manifest_version = read_manifest_version()
    pyproject_version = read_pyproject_version()
    if manifest_version != pyproject_version:
        raise SystemExit(
            "Manifest and pyproject versions differ. Align them before releasing."
        )

    return manifest_version


def replace_version(path: Path, pattern: str, new_version: str) -> None:
    content = path.read_text()
    updated_content, replacements = re.subn(
        pattern,
        rf"\g<1>{new_version}\g<3>",
        content,
        flags=re.MULTILINE,
    )
    if replacements != 1:
        raise SystemExit(
            f"Expected to update exactly one version in {path.relative_to(ROOT)}."
        )
    path.write_text(updated_content)


def update_versions(version: str, *, dry_run: bool) -> None:
    if dry_run:
        return

    manifest_data = json.loads(MANIFEST_PATH.read_text())
    manifest_data["requirements"] = [build_requirement(f"v{version}")]
    manifest_data["version"] = version
    MANIFEST_PATH.write_text(json.dumps(manifest_data, indent=2) + "\n")
    replace_version(PYPROJECT_PATH, r'^(version\s*=\s*")([^"]+)(")', version)


def run_quality_checks(*, skip_checks: bool) -> None:
    if skip_checks:
        return

    commands = [
        resolve_tool_command("ruff", module="ruff")
        + ["check", "custom_components/", "tests/"],
        resolve_tool_command("ruff", module="ruff")
        + ["format", "--check", "custom_components/", "tests/"],
        resolve_tool_command("pytest", module="pytest"),
    ]

    for command in commands:
        print(f"+ {' '.join(command)}")
        result = subprocess.run(command, cwd=ROOT, text=True)
        if result.returncode != 0:
            raise SystemExit(result.returncode)


def create_commit_and_tag(version: str, *, dry_run: bool) -> None:
    tag_name = f"v{version}"
    if dry_run:
        git_add_paths = (
            f"{MANIFEST_PATH.relative_to(ROOT)} {PYPROJECT_PATH.relative_to(ROOT)}"
        )
        print(
            f"[dry-run] Would run: git add {git_add_paths}"
        )
        print(f'[dry-run] Would run: git commit -m "Prepare {tag_name} release"')
        print(f'[dry-run] Would run: git tag -a {tag_name} -m "Release {tag_name}"')
        return

    run_command(
        [
            "git",
            "add",
            str(MANIFEST_PATH.relative_to(ROOT)),
            str(PYPROJECT_PATH.relative_to(ROOT)),
        ]
    )
    run_command(["git", "commit", "-m", f"Prepare {tag_name} release"])
    run_command(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"])


def push_release(tag_name: str, *, push: bool, dry_run: bool) -> None:
    if not push:
        return

    commands = [["git", "push", "origin", "HEAD"], ["git", "push", "origin", tag_name]]
    for command in commands:
        if dry_run:
            print(f"[dry-run] Would run: {' '.join(command)}")
            continue
        run_command(command)


def create_github_release(
    tag_name: str, *, github_release: bool, dry_run: bool
) -> None:
    if not github_release:
        return

    command = [
        "gh",
        "release",
        "create",
        tag_name,
        "--generate-notes",
        "--title",
        tag_name,
    ]
    if dry_run:
        print(f"[dry-run] Would run: {' '.join(command)}")
        return
    run_command(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a new release by updating versions, tagging, and optionally "
            "pushing."
        )
    )
    parser.add_argument("version", help="New semantic version, for example 0.1.2")
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip ruff and pytest before creating the release commit/tag.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push the release commit and tag to origin.",
    )
    parser.add_argument(
        "--github-release",
        action="store_true",
        help="Create a GitHub release with generated notes via gh.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without modifying files or git state.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not VERSION_PATTERN.match(args.version):
        print("Version must match semantic version format: X.Y.Z", file=sys.stderr)
        return 1

    if args.github_release and not args.push:
        print(
            "--github-release requires --push so the tag exists on GitHub.",
            file=sys.stderr,
        )
        return 1

    current_version = read_current_version()
    if args.version == current_version:
        print(f"Version is already {args.version}.", file=sys.stderr)
        return 1

    tag_name = f"v{args.version}"

    require_clean_git_tree()
    require_tag_absent(tag_name)

    print(f"Current version: {current_version}")
    print(f"New version: {args.version}")
    update_versions(args.version, dry_run=args.dry_run)
    run_quality_checks(skip_checks=args.skip_checks)
    create_commit_and_tag(args.version, dry_run=args.dry_run)
    push_release(tag_name, push=args.push, dry_run=args.dry_run)
    create_github_release(
        tag_name, github_release=args.github_release, dry_run=args.dry_run
    )

    if args.dry_run:
        print("Dry run complete.")
    else:
        print(f"Release {tag_name} prepared successfully.")
        if not args.push:
            print(f"Next steps: git push origin HEAD && git push origin {tag_name}")
        if args.push and not args.github_release:
            release_command = (
                f"gh release create {tag_name} --generate-notes --title {tag_name}"
            )
            print(
                f"Next step: {release_command}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
