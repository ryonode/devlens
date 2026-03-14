# DevLens

A static analysis tool for Python projects. Point it at a directory and get a breakdown of imports, function call relationships, complexity metrics, and common security anti-patterns — no configuration required.

```
$ devlens analyze ./myproject

  Files       12
  Functions   87
  Classes      9
  Avg Score   34.2
  Issues       3
```

---

## Why

I kept jumping between `grep`, half-finished docs, and mental models every time I picked up an unfamiliar codebase. DevLens is the tool I wanted: run one command, get a clear picture of what the code is actually doing.

It's not a linter. It doesn't enforce style. It just helps you *understand* a project faster.

---

## Installation

**Requirements:** Python 3.10+

```bash
git clone https://github.com/yourusername/devlens.git
cd devlens
pip install -r requirements.txt
pip install -e .
```

No config files, no API keys, no internet connection needed at runtime.

---

## Usage

### CLI

```bash
# Full analysis — imports, functions, complexity, security
devlens analyze ./myproject

# Also print per-file import lists
devlens analyze ./myproject --imports

# Complexity breakdown, sorted by score
devlens complexity ./myproject
devlens complexity ./myproject --top 10
devlens complexity ./myproject --min-score 30

# Security scan
devlens security ./myproject
devlens security ./myproject --severity HIGH

# Generate dependency + call graphs as PNG
devlens graph ./myproject
devlens graph ./myproject --output ./graphs --kind deps
```

You can also run it without installing:

```bash
python main.py analyze ./myproject
```

### Desktop GUI

```bash
python devlens_gui.py
```

Opens a native desktop window. Use the Browse button to pick a folder, then click Analyze. Results are shown across five panels: Summary, Complexity, Security, Dependencies, and Call Graph.

---

## What It Analyzes

### Dependency graph

Parses every `import` and `from ... import` statement using the AST. Attempts to resolve intra-project imports to their actual file paths; falls back to the raw module name for third-party and stdlib imports.

```
devlens/cli.py       →  devlens/analyzer.py
devlens/cli.py       →  devlens/graph.py
devlens/analyzer.py  →  devlens/dependency.py
devlens/analyzer.py  →  devlens/callgraph.py
```

### Function call graph

Walks function definitions in the AST and records which named functions each one calls. Handles nested functions and method calls (`obj.method()`). The `graph` command renders this as a PNG using NetworkX + Matplotlib.

### Complexity metrics

Per file:

| Metric | Description |
|---|---|
| LOC | Non-blank, non-comment lines |
| Functions | Total `def` / `async def` |
| Classes | Total `class` definitions |
| Conditionals | `if` / `elif` / ternary |
| Loops | `for` / `while` / `async for` |
| Max nesting | Deepest control-flow nesting depth |
| Score | Weighted composite (see below) |
| Grade | A–F label derived from score |

**Scoring:**

```
score = (conditionals × 2) + (loops × 2) + (max_nesting × 5)
      + (functions × 1) + (classes × 1)
```

Grades: A ≤ 10 · B ≤ 25 · C ≤ 50 · D ≤ 100 · F > 100

### Security scanner

Checks for patterns that are commonly problematic. These are heuristics — treat findings as prompts to review, not confirmed vulnerabilities.

| Severity | Check |
|---|---|
| HIGH | `eval()` / `exec()` usage |
| HIGH | `subprocess` with `shell=True` |
| HIGH | Pickle deserialization |
| HIGH | Hardcoded secrets (API keys, passwords, tokens, AWS creds, JWTs) |
| MEDIUM | `compile()` with dynamic input |
| LOW | Weak hashing (`hashlib.md5`, `hashlib.sha1`) |
| LOW | `assert` used as a security gate |

Secret detection uses regex over string literals and will produce false positives on example values and test fixtures. Use `--severity HIGH` to cut the noise.

---

## Project Structure

```
devlens/
├── devlens/
│   ├── analyzer.py      # Orchestrates scanning + all sub-analyzers
│   ├── dependency.py    # Import extraction, dependency graph builder
│   ├── callgraph.py     # Function call graph (AST visitor)
│   ├── complexity.py    # Complexity metrics + scoring
│   ├── security.py      # Security pattern detection
│   ├── graph.py         # PNG rendering via NetworkX + Matplotlib
│   └── cli.py           # Typer CLI, Rich output
├── devlens_gui.py       # Desktop GUI (tkinter)
├── examples/
│   └── sample_project/  # Demo project with intentional issues
├── tests/
│   └── test_devlens.py  # 28 tests, no external test plugins needed
├── main.py
├── setup.py
└── requirements.txt
```

---

## Running Tests

```bash
pytest tests/ -v
```

The suite covers all five core modules plus an end-to-end integration test. No pytest plugins required.

---

## Known Limitations

- **No cross-file call resolution.** The call graph is built per-file. Calls to functions defined in other modules won't be linked unless the names happen to match.
- **Dynamic imports aren't tracked.** `__import__()`, `importlib.import_module()`, and similar patterns are ignored.
- **Secret detection has false positives.** Example values in docstrings, test fixtures, and comments will trigger the regex checks.
- **Large graphs get noisy.** The `graph` command caps rendered nodes at 40 (deps) and 50 (calls). Raise the cap in `graph.py` if needed.
- **No incremental analysis.** Every run re-scans the full directory tree.

---

## Roadmap

- [ ] JSON / SARIF output for CI integration
- [ ] Circular import detection
- [ ] Dead code detection (defined but never called)
- [ ] Type annotation coverage percentage
- [ ] HTML report export
- [ ] Incremental mode (skip unchanged files)
- [ ] `.devlens.toml` config file support
- [ ] Plugin API for custom analyzers

---

## Contributing

1. Fork and branch: `git checkout -b my-feature`
2. Make changes, add or update tests
3. Run: `pytest tests/ -v`
4. Open a pull request with a clear description

For larger changes, open an issue first to align on approach before writing code.

Code conventions: Black for formatting, type hints on all public functions, docstrings on all modules and public classes. No new runtime dependencies without discussion.

---

## License

MIT. See [LICENSE](LICENSE).

---

## Acknowledgements

Built on Python's `ast` module. Graph rendering via [NetworkX](https://networkx.org/) and [Matplotlib](https://matplotlib.org/). CLI via [Typer](https://typer.tiangolo.com/). Terminal output via [Rich](https://github.com/Textualize/rich).
