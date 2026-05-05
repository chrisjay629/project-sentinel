# Project Sentinel

Sentinel is a small Python tool that scans your code for patterns your team says are outdated or risky.

> **Sentinel does not decide what is wrong with your code. You write the rules, and Sentinel looks for them.**

---

## Why I built this

This is a portfolio project built while learning Python and developer tooling.

The problem it explores is real: teams often have old code patterns they want to catch — things like outdated imports or risky functions — but they do not always need a full, complicated linter to do it. Sentinel is a lightweight alternative where the team stays in control of every rule.

---

## How it works

The flow is simple:

1. You write rules in `sentinel.yml`
2. Sentinel scans your Python files
3. It looks for those exact patterns
4. In **preview mode**, it only reports what it found — nothing is changed
5. In **apply mode**, it adds a short comment above each matching line
6. **Rule Forge** can suggest new rules from plain English, but a human must review and approve them before they do anything

---

## Quick Start

1. Install the dependency:

```bash
pip install pyyaml
```

2. Run the safe demo to see Sentinel working immediately:

```bash
python3 sentinel.py --preview --dir demo
```

3. Sentinel will show 5 findings from `demo/demo_target.py`. Nothing is changed.

  If you see 5 findings from demo/demo_target.py, Sentinel is working correctly.

4. When you are ready to scan your own code:

```bash
python3 sentinel.py --preview
```

5. If you want Sentinel to insert comments above flagged lines:

```bash
python3 sentinel.py --apply
```

> Always run `--preview` before `--apply`. Preview is safe. Apply edits files.

---

## Project files

| File | What it does |
|---|---|
| `sentinel.py` | The main program. Runs preview, apply, and suggest-rules. |
| `rule_forge.py` | Generates suggested rules from plain-English requests. Uses a local mock generator for now — no AI API connected yet. |
| `sentinel.yml` | The active rule file. Only rules in this file are actually used by Sentinel. |
| `demo/demo_target.py` | A clean demo file used for testing Sentinel safely. |
| `.sentinel/suggested_rules.yml` | Created by Rule Forge. Review-only — not active until you manually copy approved rules into `sentinel.yml`. |
| `README.md` | This guide. |

---

## Installation

You need one dependency:

```bash
pip install pyyaml
```

That is it. No other setup required.

---

## The rule file: sentinel.yml

This is where your team defines what Sentinel looks for:

```yaml
outdated_patterns:
  "from collections import Callable": "from collections.abc import Callable"
  "import urllib2": "Use urllib.request and urllib.error instead"
  "from mock import": "from unittest.mock import"
  "import cPickle": "import pickle"
  "#\\s*TODO": "TODO comment found. Track this in your issue tracker or remove it."

ignore_paths:
  - sentinel.py
  - rule_forge.py
  - .sentinel/
  - test_code.py
  - second_test.py
```

**How to read this:**

- `outdated_patterns` is the list of things Sentinel searches for
- The **left side** is the pattern to find in your code
- The **right side** is the message or suggested fix that Sentinel will show
- `ignore_paths` is a list of files and folders Sentinel will skip — so it does not flag its own code

---

## Clean demo

A demo file lives at `demo/demo_target.py`. It contains known outdated patterns so you can safely test Sentinel without touching real code.

**Contents of `demo/demo_target.py`:**

```python
from collections import Callable
import urllib2
from mock import MagicMock
import cPickle

# TODO test Sentinel Rule Forge workflow
```

**Run the demo:**

```bash
python3 sentinel.py --preview --dir demo
```

This scans only the `demo/` folder. Nothing is changed.

**Sentinel should find 5 patterns:**

- `from collections import Callable`
- `import urllib2`
- `from mock import MagicMock`
- `import cPickle`
- `# TODO test Sentinel Rule Forge workflow`

---

## Rule Forge

Rule Forge lets you ask for suggested rules in plain English instead of writing YAML by hand.

**Example:**

```bash
python3 sentinel.py --suggest-rules "Find TODO comments"
```

Then check what was generated:

```bash
cat .sentinel/suggested_rules.yml
```

**Important things to know about Rule Forge:**

- It creates **suggested rules only** — it does not edit your code
- It does **not** change `sentinel.yml` automatically
- If `.sentinel/suggested_rules.yml` already exists, it is backed up before being overwritten
- You must **review the suggestions** and manually copy any rules you approve into `sentinel.yml`
- Only rules in `sentinel.yml` are active

---

## Preview vs Apply

### Preview — safe, read-only

```bash
python3 sentinel.py --preview
```

Shows you what Sentinel found. Does not change any files. Always run this first.

### Apply — inserts comments

```bash
python3 sentinel.py --apply
```

Adds a short comment above each flagged line in your source files, like this:

```python
# Sentinel: outdated pattern. Suggested fix: from collections.abc import Callable
from collections import Callable
```

> ⚠️ **Do not run `--apply` until you have reviewed what `--preview` found.**
> Apply edits your source files. Preview does not.

**Duplicate protection:** If a Sentinel comment already exists above a line, `--apply` will not add another one. It is safe to run more than once.

---

## Command reference

```bash
# Scan the whole project (safe)
python3 sentinel.py --preview

# Scan only the demo folder (safe, good starting point)
python3 sentinel.py --preview --dir demo

# Insert comments above flagged lines (edits files)
python3 sentinel.py --apply

# Generate suggested rules from plain English
python3 sentinel.py --suggest-rules "Find TODO comments"

# Review the suggested rules file
cat .sentinel/suggested_rules.yml
```

---

## What Sentinel does not do

- It does not automatically rewrite your code
- It does not decide what rules to use — your team writes all the rules
- It does not automatically accept Rule Forge suggestions
- It is not a replacement for a full linter like `pylint` or `flake8`
- It is a simple, safe MVP that does exactly what you tell it to

---

## Future roadmap

- Connect Rule Forge to a real AI provider (Claude, OpenAI, etc.)
- Add interactive rule approval — step through suggestions one by one
- Add pre-commit hook support — run Sentinel automatically before each commit
- Add CI / GitHub Actions support
- Add better terminal reporting
- Add unused import and function detection

---

## Core principle

> Teams define the rules. Sentinel only watches what the team tells it to watch.