"""
rule_forge.py

Sentinel Rule Forge
-------------------
Generates suggested YAML rules from a plain-English request.

Modes:
  AI mode   — uses Gemini if GEMINI_API_KEY is set in the environment.
  Mock mode — uses the local rule library if no API key is found,
              or if the AI call fails for any reason.

Workflow:
  1. Developer runs:  python3 sentinel.py --suggest-rules "Find outdated Python 2 imports"
  2. Rule Forge tries AI mode first, falls back to mock mode if needed.
  3. Suggested rules are written to .sentinel/suggested_rules.yml.
  4. Developer reviews the file before using any rules.
  5. Nothing is merged into sentinel.yml automatically.

Environment variables (optional):
  GEMINI_API_KEY        — your Gemini API key (never hardcode this)
  SENTINEL_AI_PROVIDER  — set to "gemini" to enable AI mode
"""

import os
import json
import yaml
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# MOCK RULE LIBRARY
# Each key is a category. Each value is a list of rule dicts.
# Format matches sentinel.yml so rules can be copy-pasted directly.
# ─────────────────────────────────────────────────────────────────────────────

MOCK_RULES = {

    "python2_imports": {
        "keywords": [
            "python 2", "python2", "outdated import", "old import",
            "outdated python", "deprecated import"
        ],
        "rules": [
            {
                "id": "outdated-urllib2",
                "type": "import",
                "pattern": "import urllib2",
                "message": "urllib2 is a Python 2 module. Use urllib.request or urllib.error in Python 3.",
                "severity": "warning",
                "suggested_replacement": "import urllib.request"
            },
            {
                "id": "outdated-urlparse",
                "type": "import",
                "pattern": "import urlparse",
                "message": "urlparse is a Python 2 module. Use urllib.parse in Python 3.",
                "severity": "warning",
                "suggested_replacement": "from urllib.parse import urlparse"
            },
            {
                "id": "outdated-httplib",
                "type": "import",
                "pattern": "import httplib",
                "message": "httplib is a Python 2 module. Use http.client in Python 3.",
                "severity": "warning",
                "suggested_replacement": "import http.client"
            },
            {
                "id": "outdated-cookielib",
                "type": "import",
                "pattern": "import cookielib",
                "message": "cookielib is a Python 2 module. Use http.cookiejar in Python 3.",
                "severity": "warning",
                "suggested_replacement": "import http.cookiejar"
            },
            {
                "id": "outdated-cPickle",
                "type": "import",
                "pattern": "import cPickle",
                "message": "cPickle is a Python 2 module. Use pickle in Python 3.",
                "severity": "warning",
                "suggested_replacement": "import pickle"
            },
            {
                "id": "outdated-ConfigParser",
                "type": "import",
                "pattern": "import ConfigParser",
                "message": "ConfigParser is a Python 2 module. Use configparser (lowercase) in Python 3.",
                "severity": "warning",
                "suggested_replacement": "import configparser"
            },
        ]
    },

    "deprecated_modules": {
        "keywords": [
            "deprecated", "deprecated module", "deprecated library",
            "old module", "removed module"
        ],
        "rules": [
            {
                "id": "deprecated-imp",
                "type": "import",
                "pattern": "import imp",
                "message": "The imp module is deprecated since Python 3.4 and removed in 3.12. Use importlib instead.",
                "severity": "warning",
                "suggested_replacement": "import importlib"
            },
            {
                "id": "deprecated-distutils",
                "type": "import",
                "pattern": "from distutils",
                "message": "distutils is deprecated since Python 3.10 and removed in 3.12. Use setuptools instead.",
                "severity": "warning",
                "suggested_replacement": "from setuptools"
            },
            {
                "id": "deprecated-collections-callable",
                "type": "import",
                "pattern": "from collections import Callable",
                "message": "Callable was moved to collections.abc in Python 3.3 and removed from collections in 3.10.",
                "severity": "warning",
                "suggested_replacement": "from collections.abc import Callable"
            },
            {
                "id": "deprecated-collections-mapping",
                "type": "import",
                "pattern": "from collections import Mapping",
                "message": "Mapping was moved to collections.abc in Python 3.3 and removed from collections in 3.10.",
                "severity": "warning",
                "suggested_replacement": "from collections.abc import Mapping"
            },
            {
                "id": "deprecated-mock",
                "type": "import",
                "pattern": "from mock import",
                "message": "The standalone mock package is deprecated. Use unittest.mock (included in Python 3.3+).",
                "severity": "warning",
                "suggested_replacement": "from unittest.mock import"
            },
        ]
    },

    "eval_usage": {
        "keywords": [
            "eval", "risky eval", "dangerous eval", "unsafe eval",
            "exec", "risky exec"
        ],
        "rules": [
            {
                "id": "risky-eval",
                "type": "usage",
                "pattern": r"\beval\s*\(",
                "message": "eval() executes arbitrary code and can be a serious security risk. Review carefully.",
                "severity": "error",
                "suggested_replacement": "Consider ast.literal_eval() for safe evaluation of literals."
            },
            {
                "id": "risky-exec",
                "type": "usage",
                "pattern": r"\bexec\s*\(",
                "message": "exec() executes arbitrary code dynamically. Ensure input is fully trusted.",
                "severity": "error",
                "suggested_replacement": "Refactor to avoid dynamic code execution if possible."
            },
            {
                "id": "risky-compile",
                "type": "usage",
                "pattern": r"\bcompile\s*\(",
                "message": "compile() with untrusted input is a security risk similar to eval().",
                "severity": "warning",
                "suggested_replacement": "Review whether compile() is necessary here."
            },
        ]
    },

    "todo_comments": {
        "keywords": [
            "todo", "fixme", "todo comment", "fixme comment",
            "unfinished", "hack comment"
        ],
        "rules": [
            {
                "id": "todo-comment",
                "type": "comment",
                "pattern": r"#\s*TODO",
                "message": "TODO comment found. This marks unfinished work — track it in your issue tracker.",
                "severity": "info",
                "suggested_replacement": "Create a GitHub issue or ticket and remove the TODO."
            },
            {
                "id": "fixme-comment",
                "type": "comment",
                "pattern": r"#\s*FIXME",
                "message": "FIXME comment found. This marks a known bug — make sure it is tracked.",
                "severity": "warning",
                "suggested_replacement": "Create a GitHub issue or ticket and remove the FIXME."
            },
            {
                "id": "hack-comment",
                "type": "comment",
                "pattern": r"#\s*HACK",
                "message": "HACK comment found. This marks a workaround that should be revisited.",
                "severity": "warning",
                "suggested_replacement": "Document the reason and create a ticket to address it properly."
            },
        ]
    },

    "print_statements": {
        "keywords": [
            "print", "print statement", "debug print", "leftover print",
            "console print", "debugging"
        ],
        "rules": [
            {
                "id": "debug-print",
                "type": "usage",
                "pattern": r"^\s*print\s*\(",
                "message": "print() found at the start of a line. May be a leftover debug statement.",
                "severity": "info",
                "suggested_replacement": "Use the logging module for production output."
            },
        ]
    },

    "broad_except": {
        "keywords": [
            "except", "broad except", "bare except", "catch all",
            "exception handling", "risky except"
        ],
        "rules": [
            {
                "id": "broad-except-exception",
                "type": "usage",
                "pattern": r"except\s+Exception\s*:",
                "message": "Catching 'Exception' is very broad. Catch specific exceptions where possible.",
                "severity": "warning",
                "suggested_replacement": "except SpecificError:"
            },
            {
                "id": "bare-except",
                "type": "usage",
                "pattern": r"except\s*:",
                "message": "Bare except clause catches everything including KeyboardInterrupt and SystemExit.",
                "severity": "error",
                "suggested_replacement": "except SpecificError:"
            },
        ]
    },

}


# ─────────────────────────────────────────────────────────────────────────────
# RULE VALIDATION
# Checks that every rule returned by AI has the required fields and
# allowed values before it is saved. Rejects any rule that looks wrong.
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = {"id", "type", "pattern", "message", "severity", "suggested_replacement"}
ALLOWED_TYPES = {"import", "usage", "comment", "pattern"}
ALLOWED_SEVERITIES = {"info", "warning", "error"}


def validate_rule(rule):
    """
    Returns True if a rule dict has all required fields and valid values.
    Returns False (and prints a warning) if anything looks wrong.

    This is a safety check so invalid AI output never gets saved silently.
    """
    if not isinstance(rule, dict):
        print(f"  ⚠️  Skipping invalid rule (not a dict): {rule}")
        return False

    missing = REQUIRED_FIELDS - rule.keys()
    if missing:
        print(f"  ⚠️  Skipping rule missing fields {missing}: {rule.get('id', '(no id)')}")
        return False

    if rule["type"] not in ALLOWED_TYPES:
        print(f"  ⚠️  Skipping rule with unknown type '{rule['type']}': {rule['id']}")
        return False

    if rule["severity"] not in ALLOWED_SEVERITIES:
        print(f"  ⚠️  Skipping rule with unknown severity '{rule['severity']}': {rule['id']}")
        return False

    return True


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI AI PROVIDER
# Called only when GEMINI_API_KEY is set in the environment.
# Falls back to mock mode on any error.
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_PROMPT = """
You are a Python code hygiene assistant for a tool called Sentinel.

Given a plain-English request, return a JSON array of Sentinel rules.
Each rule must follow this exact format:

[
  {{
    "id": "short-kebab-case-id",
    "type": "import | usage | comment | pattern",
    "pattern": "regex or plain string to search for",
    "message": "clear explanation of why this is outdated or risky",
    "severity": "info | warning | error",
    "suggested_replacement": "what to use instead"
  }}
]

Rules:
- Return only a valid JSON array. No explanation, no markdown, no code blocks.
- Use "import" type for import statements.
- Use "usage" type for function calls or syntax patterns.
- Use "comment" type for comment patterns.
- Use "pattern" for anything else.
- severity must be exactly one of: info, warning, error.
- Patterns should be plain strings unless a regex is clearly needed.

Request: {request}
"""


def generate_rules_with_ai(request):
    """
    Calls the Gemini API to generate rules from the plain-English request.

    How it works:
    1. Reads GEMINI_API_KEY from the environment (never hardcoded).
    2. Checks SENTINEL_AI_PROVIDER is set to "gemini".
    3. Sends the request to Gemini with a strict JSON-only prompt.
    4. Parses and validates the response.
    5. Returns a list of valid rule dicts, or an empty list on any failure.

    Returning an empty list tells generate_suggested_rules() to use mock mode.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    provider = os.environ.get("SENTINEL_AI_PROVIDER", "").strip().lower()

    if not api_key or provider != "gemini":
        return []

    try:
        from google import genai
    except ImportError:
        print("  ⚠️  google-genai is not installed. Falling back to mock mode.")
        print("       Run: pip install google-genai")
        return []

    try:
        client = genai.Client(api_key=api_key)

        prompt = GEMINI_PROMPT.format(request=request)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text.strip()

        # Strip markdown code fences if Gemini wraps the JSON anyway
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        rules = json.loads(raw)

        if not isinstance(rules, list):
            print("  ⚠️  Gemini returned unexpected format. Falling back to mock mode.")
            return []

        # Validate every rule — skip any that fail
        valid_rules = [r for r in rules if validate_rule(r)]

        if not valid_rules:
            print("  ⚠️  No valid rules in Gemini response. Falling back to mock mode.")
            return []

        return valid_rules

    except json.JSONDecodeError:
        print("  ⚠️  Gemini response was not valid JSON. Falling back to mock mode.")
        return []
    except Exception as e:
        print(f"  ⚠️  Gemini API error: {e}. Falling back to mock mode.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# CORE RULE FORGE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def match_request_to_category(request):
    """
    Takes the developer's plain-English request and finds the best matching
    category in the MOCK_RULES library.

    How it works:
    - Lowercases the request.
    - Checks if any keyword from each category appears in the request.
    - Returns the first matching category name, or None if nothing matches.
    """
    request_lower = request.lower()

    for category, data in MOCK_RULES.items():
        for keyword in data["keywords"]:
            if keyword in request_lower:
                return category

    return None


def generate_suggested_rules(request):
    """
    Main rule generation function.

    1. Tries Gemini AI if GEMINI_API_KEY and SENTINEL_AI_PROVIDER=gemini are set.
    2. Falls back to the local mock library if AI is unavailable or fails.
    3. Returns a tuple: (rules list, mode string)
       mode is either "ai (gemini)" or "mock (local)"
    """
    ai_rules = generate_rules_with_ai(request)
    if ai_rules:
        return ai_rules, "ai (gemini)"

    category = match_request_to_category(request)
    if category:
        return MOCK_RULES[category]["rules"], "mock (local)"

    return [], "mock (local)"


def write_suggested_rules(request, rules, mode):
    """
    Writes the suggested rules to .sentinel/suggested_rules.yml.

    - Creates the .sentinel/ folder if it does not exist.
    - If suggested_rules.yml already exists, backs it up before overwriting.
    - Stamps the generator mode (AI or mock) in the file header.
    - Returns the path to the written file.
    """
    sentinel_dir = ".sentinel"
    os.makedirs(sentinel_dir, exist_ok=True)

    output_path = os.path.join(sentinel_dir, "suggested_rules.yml")

    # Back up any existing file before overwriting
    if os.path.exists(output_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(sentinel_dir, f"suggested_rules_backup_{timestamp}.yml")
        os.rename(output_path, backup_path)
        print(f"\n  ⚠️  Existing suggested_rules.yml backed up to: {backup_path}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# ─────────────────────────────────────────────────────\n")
        f.write("# Sentinel Rule Forge — SUGGESTED RULES\n")
        f.write("# ─────────────────────────────────────────────────────\n")
        f.write("# These rules were generated from your request:\n")
        f.write(f'#   "{request}"\n')
        f.write("#\n")
        f.write(f"# Generator : {mode}\n")
        f.write("# Status    : For review only. Not active.\n")
        f.write("# To use    : copy approved rules into sentinel.yml\n")
        f.write("# ─────────────────────────────────────────────────────\n\n")
        f.write(f"# Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f'# Request   : "{request}"\n\n')

        yaml.dump({"rules": rules}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return output_path


def run_rule_forge(request: str) -> None:
    """
    Entry point for the --suggest-rules command.
    Orchestrates the full Rule Forge workflow:
      1. Generate suggested rules from the request.
      2. Write them to .sentinel/suggested_rules.yml.
      3. Print a clear summary to the terminal.
    """
    print(f"\n  Sentinel Rule Forge")
    print(f"  ─────────────────────────────────────────")
    print(f"  Request: \"{request}\"")
    print(f"  Generating suggested rules...\n")

    rules, mode = generate_suggested_rules(request)

    if mode == "ai (gemini)":
        print(f"  ✓ Mode: AI (Gemini)")
    else:
        print(f"  ✓ Mode: mock/local (no API key or AI unavailable)")

    if not rules:
        print("  No matching rules found for that request.")
        print("  Try one of these:\n")
        print("    python3 sentinel.py --suggest-rules \"Find outdated Python 2 imports\"")
        print("    python3 sentinel.py --suggest-rules \"Find deprecated Python modules\"")
        print("    python3 sentinel.py --suggest-rules \"Find risky eval usage\"")
        print("    python3 sentinel.py --suggest-rules \"Find TODO comments\"")
        print("    python3 sentinel.py --suggest-rules \"Find print statements\"")
        print("    python3 sentinel.py --suggest-rules \"Find broad except statements\"\n")
        return

    output_path = write_suggested_rules(request, rules, mode)

    print(f"  ✓ {len(rules)} rule(s) suggested.\n")
    print(f"  Saved to: {output_path}\n")
    print(f"  ─────────────────────────────────────────")
    print(f"  Rules suggested (review before using):\n")

    for rule in rules:
        print(f"    [{rule['severity'].upper()}]  {rule['id']}")
        print(f"    Pattern : {rule['pattern']}")
        print(f"    Message : {rule['message']}")
        print()

    print(f"  ─────────────────────────────────────────")
    print(f"  Next steps:")
    print(f"    1. Open .sentinel/suggested_rules.yml")
    print(f"    2. Review the suggested rules")
    print(f"    3. Copy any rules you approve into sentinel.yml")
    print(f"    4. Run: python3 sentinel.py --preview\n")