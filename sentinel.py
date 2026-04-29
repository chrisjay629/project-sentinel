import re
import argparse
from pathlib import Path
import yaml


def load_rules(config_path="sentinel.yml"):
    """
    Opens sentinel.yml and reads your team's outdated patterns.
    """
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config["outdated_patterns"]


def scan_file(filepath, outdated_patterns):
    """
    Scans one Python file for outdated patterns.
    """
    findings = []
    path = Path(filepath)

    with path.open("r", encoding="utf-8") as file:
        lines = file.readlines()

    for line_number, line in enumerate(lines, start=1):
        stripped_line = line.strip()

        for pattern, replacement in outdated_patterns.items():
            if re.search(pattern, stripped_line):
                findings.append({
                    "file": str(path),
                    "line_number": line_number,
                    "original_line": stripped_line,
                    "matched_pattern": pattern,
                    "suggested_replacement": replacement,
                })

    return findings


def scan_directory(directory_path, outdated_patterns):
    """
    Scans every .py file inside a folder.
    """
    all_findings = []
    folder = Path(directory_path)

    python_files = folder.rglob("*.py")

    for python_file in python_files:
        findings = scan_file(python_file, outdated_patterns)
        all_findings.extend(findings)

    return all_findings


def preview(findings):
    """
    Shows findings in the terminal without editing files.
    """
    if not findings:
        print("\nSentinel: no outdated patterns found. Your code looks clean.\n")
        return

    print(f"\nSentinel found {len(findings)} outdated pattern(s):\n")
    print("-" * 60)

    for finding in findings:
        print(f"File : {finding['file']}")
        print(f"Line : {finding['line_number']}")
        print(f"Found: {finding['original_line']}")
        print(f"Fix  : {finding['suggested_replacement']}")
        print("-" * 60)


def apply_comments(findings):
    """
    Inserts a Sentinel comment above each outdated line.
    Avoids adding duplicate Sentinel comments.
    """
    if not findings:
        print("\nSentinel: nothing to apply. No outdated patterns found.\n")
        return

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

        changed_this_file = False

        for finding in sorted(file_findings, key=lambda item: item["line_number"], reverse=True):
            line_index = finding["line_number"] - 1

            sentinel_comment = (
                f"# Sentinel: outdated pattern. "
                f"Suggested fix: {finding['suggested_replacement']}\n"
            )

            previous_line_index = line_index - 1

            if previous_line_index >= 0 and "Sentinel:" in lines[previous_line_index]:
                continue

            lines.insert(line_index, sentinel_comment)
            changed_this_file = True

        if changed_this_file:
            with path.open("w", encoding="utf-8") as file:
                file.writelines(lines)

            files_changed += 1

    print(f"\nSentinel: comments inserted into {files_changed} file(s).\n")


def main():
    """
    Reads the terminal command and runs the correct mode.
    """
    parser = argparse.ArgumentParser(
        description="Sentinel — find outdated patterns defined by your team."
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show findings only. Does not edit files."
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Insert Sentinel comments above outdated lines."
    )

    parser.add_argument(
        "--config",
        default="sentinel.yml",
        help="Path to sentinel.yml. Default is sentinel.yml."
    )

    parser.add_argument(
        "--dir",
        default=".",
        help="Folder to scan. Default is the current folder."
    )

    args = parser.parse_args()

    rules = load_rules(args.config)
    findings = scan_directory(args.dir, rules)

    if args.apply:
        apply_comments(findings)
    else:
        preview(findings)

    raise SystemExit(0)


if __name__ == "__main__":
    main()