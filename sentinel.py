"""
sentinel.py

Project Sentinel — local code hygiene tool.

Commands:
  --preview          Scan and print findings. Does not edit files.
  --apply            Insert Sentinel comments above flagged lines.
  --suggest-rules    Generate suggested YAML rules from a plain-English request.

Default (no flag): runs --preview.

The team defines the rules. Sentinel only watches what the team tells it to.
"""

import re
import argparse
from pathlib import Path
import yaml

from rule_forge import run_rule_forge


# ─────────────────────────────────────────
# STEP 1: Load rules from sentinel.yml
# ─────────────────────────────────────────

def load_rules(config_path="sentinel.yml"):
    """
    Opens sentinel.yml and reads your team's outdated patterns.
    Also reads the optional ignore_paths list.
    Returns a tuple: (outdated_patterns dict, ignore_paths list)

    If ignore_paths is missing from sentinel.yml, returns an empty list
    so the rest of the code does not need to handle None.
    """
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    patterns = config["outdated_patterns"]
    ignore_paths = config.get("ignore_paths", [])
    return patterns, ignore_paths


# ─────────────────────────────────────────
# STEP 2: Scan a single file for matches
# ─────────────────────────────────────────

def scan_file(filepath, outdated_patterns):
    """
    Reads one Python file line by line.
    If a line matches any pattern in sentinel.yml, it records a finding.
    Returns a list of findings for that file.
    """
    findings = []
    path = Path(filepath)

    with path.open("r", encoding="utf-8") as file:
        lines = file.readlines()

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        for pattern, replacement in outdated_patterns.items():
            if re.search(pattern, stripped):
                findings.append({
                    "file": str(path),
                    "line_number": line_number,
                    "original_line": stripped,
                    "matched_pattern": pattern,
                    "suggested_replacement": replacement,
                })

    return findings


# ─────────────────────────────────────────
# STEP 3: Scan all .py files in a folder
# ─────────────────────────────────────────

def is_ignored(filepath, ignore_paths):
    """
    Returns True if a file should be skipped based on ignore_paths.

    How it works:
    - Resolves the scanned file to an absolute path (e.g. /project/sentinel.py)
    - Resolves each ignore entry to an absolute path too
    - For files: checks if the resolved paths are identical
    - For folders: checks if the file lives inside the resolved folder

    This means sentinel.py, ./sentinel.py, and /full/path/sentinel.py
    all behave the same way.
    """
    resolved_file = Path(filepath).resolve()

    for ignored in ignore_paths:
        # A trailing slash explicitly marks this entry as a folder
        is_folder_entry = ignored.endswith("/")
        ignored_path = Path(ignored.rstrip("/")).resolve()

        if is_folder_entry or ignored_path.is_dir():
            # Folder match: check if the file lives inside the ignored folder
            if resolved_file.is_relative_to(ignored_path):
                return True
        else:
            # File match: check if the paths are exactly the same file
            if resolved_file == ignored_path:
                return True

    return False


def scan_directory(directory_path, outdated_patterns, ignore_paths=None):
    """
    Walks through every folder and sub-folder in your project.
    Calls scan_file() on every .py file it finds.
    Skips files matching any entry in ignore_paths.
    Returns one combined list of all findings.
    """
    if ignore_paths is None:
        ignore_paths = []

    all_findings = []
    for python_file in Path(directory_path).rglob("*.py"):
        if is_ignored(python_file, ignore_paths):
            continue
        all_findings.extend(scan_file(python_file, outdated_patterns))
    return all_findings


# ─────────────────────────────────────────
# MODE 1: --preview
# Prints findings to the terminal. Does NOT edit any files.
# ─────────────────────────────────────────

def preview(findings):
    """
    Shows you everything Sentinel found — safely, without touching your code.
    Always the right first step before running --apply.
    """
    if not findings:
        print("\n  Sentinel: no outdated patterns found. Your code looks clean.\n")
        return

    print(f"\n  Sentinel found {len(findings)} outdated pattern(s):\n")
    print("  " + "─" * 54)

    for finding in findings:
        print(f"  File : {finding['file']}")
        print(f"  Line : {finding['line_number']}")
        print(f"  Found: {finding['original_line']}")
        print(f"  Fix  : {finding['suggested_replacement']}")
        print("  " + "─" * 54)


# ─────────────────────────────────────────
# MODE 2: --apply
# Inserts a # Sentinel: comment above each flagged line.
# Skips lines that already have a Sentinel comment above them.
# ─────────────────────────────────────────

def apply_comments(findings):
    """
    Goes through each flagged file and inserts a comment above
    the outdated line explaining what should be changed.

    Example result in your file:
      # Sentinel: outdated pattern. Suggested fix: from collections.abc import Callable
      from collections import Callable

    Duplicate protection: if a Sentinel comment is already above
    a line, it will not insert another one.
    """
    if not findings:
        print("\n  Sentinel: nothing to apply. No outdated patterns found.\n")
        return

    # Group all findings by which file they belong to
    findings_by_file = {}
    for finding in findings:
        file_path = finding["file"]
        if file_path not in findings_by_file:
            findings_by_file[file_path] = []
        findings_by_file[file_path].append(finding)

    files_changed = 0

    for file_path, file_findings in findings_by_file.items():
        path = Path(file_path)

        with path.open("r", encoding="utf-8") as file:
            lines = file.readlines()

        # Process findings bottom-to-top so inserting lines
        # doesn't shift the line numbers of earlier findings
        for finding in sorted(file_findings, key=lambda x: x["line_number"], reverse=True):
            line_index = finding["line_number"] - 1

            comment = (
                f"# Sentinel: outdated pattern. "
                f"Suggested fix: {finding['suggested_replacement']}\n"
            )

            # Duplicate protection: check the line above
            previous_index = line_index - 1
            if previous_index >= 0 and "Sentinel:" in lines[previous_index]:
                continue

            lines.insert(line_index, comment)

        with path.open("w", encoding="utf-8") as file:
            file.writelines(lines)

        files_changed += 1

    print(f"\n  Sentinel: comments inserted into {files_changed} file(s).")
    print("  Tip: run --preview again to see the updated state.\n")


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────

def main():
    """
    Reads your command and runs the right mode.
    """
    parser = argparse.ArgumentParser(
        description="Sentinel — find outdated patterns defined by your team.",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print findings to the terminal. Does not edit any files.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Insert a Sentinel comment above each outdated line.",
    )
    parser.add_argument(
        "--suggest-rules",
        metavar="REQUEST",
        help="Generate suggested YAML rules from a plain-English description.",
    )
    parser.add_argument(
        "--config",
        default="sentinel.yml",
        help="Path to your sentinel.yml file (default: sentinel.yml).",
    )
    parser.add_argument(
        "--dir",
        default=".",
        help="Folder to scan (default: current folder).",
    )

    args = parser.parse_args()

    # ── Rule Forge mode ──────────────────
    if args.suggest_rules:
        run_rule_forge(args.suggest_rules)
        return

    # ── Scan modes ───────────────────────
    rules, ignore_paths = load_rules(args.config)
    findings = scan_directory(args.dir, rules, ignore_paths)

    # Default to --preview if no mode flag is given
    if not args.apply:
        preview(findings)

    if args.apply:
        apply_comments(findings)

    # Exit code 1 if findings exist (useful for CI / pre-commit hooks later)
    raise SystemExit(1 if findings else 0)


if __name__ == "__main__":
    main()