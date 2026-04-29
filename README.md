# Project Sentinel

## Version

Current version: MVP 0.1

A lightweight local code hygiene tool for Python projects.

---

## What is Sentinel?

Sentinel scans your Python files for outdated code patterns — things like old imports or deprecated syntax — and either shows you what it found or adds a helpful comment above the flagged line.

The key idea: **Sentinel does not decide what is outdated. Your team does.**

You write the rules in a plain text file called `sentinel.yml`. Sentinel reads those rules and watches for them. Nothing more.

---

## Why use Sentinel?

Most linters come with a fixed set of rules someone else decided on. Sentinel is different — it only tracks what your team explicitly tells it to track. This makes it practical for:

- Teams migrating from Python 2 patterns to Python 3
- Projects with known deprecated imports that keep sneaking back in
- New developers who need a safety net while learning the codebase
- Any team that wants a simple, readable, zero-config hygiene tool

---

## Project files

| File | What it does |
|---|---|
| `sentinel.py` | The tool itself — runs the scan |
| `sentinel.yml` | Your team's rule file — defines what is outdated |
| `README.md` | This guide |

---

## How the rules work

Open `sentinel.yml` and add any patterns you want Sentinel to watch for:

```yaml
outdated_patterns:
  "import urllib2": "Use urllib.request and urllib.error instead"
  "from mock import": "from unittest.mock import"
  "from collections import Callable": "from collections.abc import Callable"
  "import cPickle": "import pickle"
```

Each line is:
- **left side** — the outdated pattern to look for (Sentinel searches for this in every `.py` file)
- **right side** — what Sentinel recommends instead (shown in the terminal or inserted as a comment)

That's it. No config files, no complex setup. Your team adds a line and Sentinel starts watching for it.

---


## Installation

Sentinel has one dependency: `PyYAML`, which lets Python read `.yml` files.

```bash
python3 -m pip install PyYAML

Then copy `sentinel.py` and `sentinel.yml` into your project root. You're ready to go.

---

## How to use Sentinel

Sentinel has two modes. Always start with `--preview`.

### --preview mode (safe, read-only)

```bash
python3 sentinel.py --preview
```

Scans every `.py` file in your project and prints findings to the terminal. **Does not edit any files.** This is the right first step — run it as many times as you like with zero risk.

Example output:

```
  Sentinel found 2 outdated pattern(s):

  ──────────────────────────────────────────────────────
  File : ./my_module.py
  Line : 4
  Found: from collections import Callable
  Fix  : from collections.abc import Callable
  ──────────────────────────────────────────────────────
  File : ./utils.py
  Line : 12
  Found: import urllib2
  Fix  : Use urllib.request and urllib.error instead
  ──────────────────────────────────────────────────────
```

---

### --apply mode (inserts comments)

```bash
python3 sentinel.py --apply
```

Inserts a comment directly above each flagged line in your source file, like this:

```python
# Sentinel: outdated pattern. Suggested fix: from collections.abc import Callable
from collections import Callable
```

The comment tells your team exactly what needs changing and why — without automatically rewriting any code. You stay in control.

**Duplicate protection:** If a Sentinel comment already exists above a line, `--apply` will not add another one. Running it multiple times is safe.

---

### Default mode (no flag)

```bash
python3 sentinel.py
```

Runs `--preview` automatically. No files are ever changed unless you explicitly pass `--apply`.

---

## Options

| Flag | What it does |
|---|---|
| `--preview` | Print findings to the terminal. No files changed. |
| `--apply` | Insert Sentinel comments above flagged lines. |
| `--dir path/` | Scan a specific subfolder instead of the whole project. |
| `--config path/sentinel.yml` | Use a config file in a different location. |

Examples:

```bash
# Scan only the src/ folder
python3 sentinel.py --preview --dir src/

# Use a config file stored in a tools/ folder
python3 sentinel.py --preview --config tools/sentinel.yml
```

---

## What Sentinel does not do

- Sentinel does not automatically rewrite your code
- Sentinel does not decide what is outdated — your team does
- Sentinel does not run silently in the background (unless you add it to a pre-commit hook later)
- Sentinel does not have opinions about style or formatting — only what you define in `sentinel.yml`

---

## Team setup

To share Sentinel with your team:

1. Add `sentinel.py` and `sentinel.yml` to version control
2. Each teammate runs `pip install pyyaml` once
3. When the team discovers a new outdated pattern, add one line to `sentinel.yml` and commit it
4. Everyone's copy of Sentinel now watches for that pattern automatically

Adding a new rule is a one-line pull request.

---

## Future roadmap

These features are planned but not part of the current MVP:

- **Pre-commit hook** — run Sentinel automatically before every `git commit`
- **CI/CD integration** — run Sentinel on every pull request via GitHub Actions
- **IDE extension** — show flagged lines inline in your editor with squiggles
- **Background watch mode** — auto-scan when a file is saved
- **Unused import detection** — find imports your code never uses (AST-based)
- **Unused function detection** — find dead code in your project
- **Watched dependency updates** — flag outdated packages in requirements files
- **AI explanation layer** — explain why a pattern is outdated using an LLM
- **Advanced autofix mode** — rewrite flagged lines automatically (with confirmation)

---

## Core principle

> Teams define the rules. Sentinel only watches what the team tells it to watch.

Sentinel is designed to stay simple, stay readable, and stay in your control.