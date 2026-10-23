"""Read-only checks for portfolio export manifests. Python 3.10+, no dependencies."""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sys


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_manifest(manifest, root):
    """Return issues without changing files or contacting external services."""
    issues = []
    root = Path(root).resolve()
    seen = set()

    def check_asset(asset, label):
        if not isinstance(asset, dict):
            issues.append(f"{label}: expected an object")
            return
        name = asset.get("file")
        if not isinstance(name, str) or not name.strip():
            issues.append(f"{label}: file must be a non-empty relative path")
            return
        # Use forward slashes so the same manifest works on Windows and Unix.
        if "\\" in name or PureWindowsPath(name).drive or Path(name).is_absolute():
            issues.append(f"{label}: use a relative path with forward slashes")
            return
        try:
            path = (root / name).resolve()
            path.relative_to(root)
        except (ValueError, OSError, RuntimeError):
            issues.append(f"{label}: path must stay inside the manifest directory")
            return
        if path in seen:
            issues.append(f"{label}: source and exports must reference distinct files")
        seen.add(path)
        expected = asset.get("sha256")
        valid_hash = isinstance(expected, str) and re.fullmatch(r"[0-9a-fA-F]{64}", expected)
        if not valid_hash:
            issues.append(f"{label}: record a 64-character SHA-256 hash")
        try:
            if not path.is_file():
                issues.append(f"{label}: file does not exist or is not a regular file")
                return
            if path.stat().st_size == 0:
                issues.append(f"{label}: file is empty")
            if valid_hash and sha256(path) != expected.lower():
                issues.append(f"{label}: file hash differs from the recorded hash")
        except OSError:
            issues.append(f"{label}: file cannot be read")

    if not isinstance(manifest, dict):
        return ["manifest: expected an object"]
    if not isinstance(manifest.get("project"), str) or not manifest["project"].strip():
        issues.append("project: provide a non-empty project name")
    check_asset(manifest.get("source"), "source")
    exports = manifest.get("exports")
    if not isinstance(exports, list) or not exports:
        issues.append("exports: provide at least one export")
        return issues
    for index, asset in enumerate(exports):
        label = f"exports[{index}]"
        check_asset(asset, label)
        if not isinstance(asset, dict):
            continue
        for dimension in ("width", "height"):
            value = asset.get(dimension)
            if type(value) is not int or value <= 0:
                issues.append(f"{label}.{dimension}: provide a positive integer")
        if asset.get("reviewed") is not True:
            issues.append(f"{label}: complete the human visual review before setting reviewed to true")
    return issues


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    hash_command = commands.add_parser("hash", help="Print a file's SHA-256; does not modify it")
    hash_command.add_argument("file", type=Path)
    check_command = commands.add_parser("check", help="Check files relative to a manifest's directory")
    check_command.add_argument("manifest", type=Path)
    check_command.add_argument("--json", action="store_true", help="Return machine-readable results")
    args = parser.parse_args(argv)
    if args.command == "hash":
        try:
            print(sha256(args.file))
            return 0
        except OSError:
            print("File cannot be read.", file=sys.stderr)
            return 2
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        if args.json:
            print(json.dumps({"ok": False, "issues": ["Cannot read a valid UTF-8 JSON manifest"]}))
        else:
            print("Cannot read a valid UTF-8 JSON manifest.", file=sys.stderr)
        return 2
    issues = check_manifest(manifest, args.manifest.parent)
    if args.json:
        print(json.dumps({"ok": not issues, "issues": issues}, indent=2))
    elif issues:
        print("Manifest checks failed:\n" + "\n".join(f"- {issue}" for issue in issues))
    else:
        print("Manifest checks passed. Visual content, permissions and platform approval still require review.")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
