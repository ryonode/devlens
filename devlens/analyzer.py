"""
DevLens - Core Analyzer Module
Orchestrates all analysis components for a Python codebase.
"""

from __future__ import annotations

import ast
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False
    Console = None  # type: ignore

from .dependency import DependencyAnalyzer
from .callgraph import CallGraphAnalyzer
from .complexity import ComplexityAnalyzer
from .security import SecurityScanner

console = Console() if _RICH_AVAILABLE else None

def _print(msg: str) -> None:
    """Safe print that strips Rich markup when Rich is unavailable."""
    if _RICH_AVAILABLE and console:
        console.print(msg)
    else:
        import re
        clean = re.sub(r"\[/?[^\]]+\]", "", msg)
        print(clean)

# Directories to skip during scanning
IGNORED_DIRS = {
    ".venv", "venv", "env", ".env",
    "__pycache__", ".git", ".tox",
    "node_modules", ".mypy_cache", ".pytest_cache",
    "dist", "build", "*.egg-info",
}


@dataclass
class FileResult:
    """Holds all analysis results for a single Python file."""
    path: Path
    relative_path: str
    imports: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    call_graph: dict[str, list[str]] = field(default_factory=dict)
    complexity: dict = field(default_factory=dict)
    security_issues: list[dict] = field(default_factory=list)
    parse_error: Optional[str] = None


@dataclass
class ProjectReport:
    """Complete analysis report for an entire project."""
    root: Path
    scanned_at: float = field(default_factory=time.time)
    files: list[FileResult] = field(default_factory=list)
    total_files: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_security_issues: int = 0
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    global_call_graph: dict[str, list[str]] = field(default_factory=dict)

    @property
    def avg_complexity(self) -> float:
        scores = [
            f.complexity.get("score", 0)
            for f in self.files
            if not f.parse_error
        ]
        return round(sum(scores) / len(scores), 2) if scores else 0.0

    @property
    def most_complex_files(self) -> list[FileResult]:
        return sorted(
            [f for f in self.files if not f.parse_error],
            key=lambda f: f.complexity.get("score", 0),
            reverse=True,
        )[:5]


class _DummyTask:
    """No-op task for when Rich is unavailable."""
    pass


class _DummyProgress:
    """No-op progress context for when Rich is unavailable."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def add_task(self, desc: str, **kwargs) -> _DummyTask:
        print(f"  {desc}")
        return _DummyTask()

    def update(self, task, **kwargs):
        pass

    def advance(self, task, amount: int = 1):
        pass


class ProjectScanner:
    """Scans a directory tree and collects all Python source files."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"Directory not found: {self.root}")
        if not self.root.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.root}")

    def scan(self) -> list[Path]:
        """Return list of .py files, ignoring venvs and caches."""
        py_files: list[Path] = []

        for path in self.root.rglob("*.py"):
            # Check if any part of the path is in IGNORED_DIRS
            parts = set(path.relative_to(self.root).parts)
            if parts & IGNORED_DIRS:
                continue
            # Also skip egg-info and dist-info directories
            if any(p.endswith((".egg-info", ".dist-info")) for p in parts):
                continue
            py_files.append(path)

        return sorted(py_files)


class DevLensAnalyzer:
    """
    Main analysis engine for DevLens.
    Coordinates scanning, parsing, and all sub-analyzers.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.scanner = ProjectScanner(root)
        self.dep_analyzer = DependencyAnalyzer()
        self.cg_analyzer = CallGraphAnalyzer()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.security_scanner = SecurityScanner()

    def analyze(self, verbose: bool = False) -> ProjectReport:
        """
        Run full analysis on the project.

        Args:
            verbose: Show detailed progress output.

        Returns:
            ProjectReport with all analysis results.
        """
        report = ProjectReport(root=self.root)

        if _RICH_AVAILABLE and console:
            ctx = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
                transient=True,
            )
        else:
            ctx = _DummyProgress()

        with ctx as progress:
            # Step 1: Scan files
            scan_task = progress.add_task("Scanning files...", total=None)
            py_files = self.scanner.scan()
            report.total_files = len(py_files)
            progress.update(scan_task, completed=True, total=1)

            if not py_files:
                _print("[yellow]No Python files found.[/yellow]")
                return report

            # Step 2: Parse and analyze each file
            analyze_task = progress.add_task(
                "Analyzing files...", total=len(py_files)
            )

            for py_file in py_files:
                rel = str(py_file.relative_to(self.root))
                file_result = FileResult(path=py_file, relative_path=rel)

                try:
                    source = py_file.read_text(encoding="utf-8", errors="replace")
                    tree = ast.parse(source, filename=str(py_file))
                except SyntaxError as e:
                    file_result.parse_error = str(e)
                    report.files.append(file_result)
                    progress.advance(analyze_task)
                    continue

                # Run all analyzers
                file_result.imports = self.dep_analyzer.extract_imports(tree)
                file_result.functions, file_result.classes = self._extract_definitions(tree)
                file_result.call_graph = self.cg_analyzer.extract_calls(tree)
                file_result.complexity = self.complexity_analyzer.analyze(tree, source)
                file_result.security_issues = self.security_scanner.scan(tree, source, rel)

                report.files.append(file_result)
                progress.advance(analyze_task)

            # Step 3: Build project-level graphs
            build_task = progress.add_task("Building graphs...", total=1)
            report.dependency_graph = self.dep_analyzer.build_project_graph(
                report.files, self.root
            )
            report.global_call_graph = self._merge_call_graphs(report.files)
            progress.update(build_task, completed=1)

        # Aggregate totals
        for f in report.files:
            report.total_functions += len(f.functions)
            report.total_classes += len(f.classes)
            report.total_security_issues += len(f.security_issues)

        return report

    @staticmethod
    def _extract_definitions(tree: ast.AST) -> tuple[list[str], list[str]]:
        """Extract top-level function and class names from AST."""
        functions, classes = [], []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
        return functions, classes

    @staticmethod
    def _merge_call_graphs(files: list[FileResult]) -> dict[str, list[str]]:
        """Merge per-file call graphs into a global call graph."""
        merged: dict[str, list[str]] = {}
        for f in files:
            for caller, callees in f.call_graph.items():
                key = f"{f.relative_path}::{caller}"
                merged[key] = callees
        return merged
