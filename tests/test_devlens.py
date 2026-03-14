"""
DevLens – Test Suite
"""

from __future__ import annotations

import ast
import textwrap
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

SIMPLE_SOURCE = textwrap.dedent("""\
    import os
    import sys
    from pathlib import Path

    def greet(name: str) -> str:
        return f"Hello, {name}"

    def shout(name: str) -> str:
        return greet(name).upper()

    class Greeter:
        def __init__(self, prefix: str = "Hello"):
            self.prefix = prefix

        def greet(self, name: str) -> str:
            return f"{self.prefix}, {name}"
""")

COMPLEX_SOURCE = textwrap.dedent("""\
    def complex_function(x, y, z):
        if x > 0:
            if y > 0:
                for i in range(x):
                    if i % 2 == 0:
                        while z > 0:
                            z -= 1
                    else:
                        pass
            elif y < 0:
                for j in range(abs(y)):
                    pass
        else:
            for k in range(10):
                if k > 5:
                    pass
        return x + y + z
""")

INSECURE_SOURCE = textwrap.dedent("""\
    import subprocess
    SECRET_KEY = "abc123secretkey"

    def run(cmd):
        subprocess.run(cmd, shell=True)

    def dangerous(code):
        eval(code)
        exec(code)
""")


def _parse(source: str) -> ast.AST:
    return ast.parse(source)


# ---------------------------------------------------------------------------
# DependencyAnalyzer tests
# ---------------------------------------------------------------------------

class TestDependencyAnalyzer:
    def setup_method(self):
        from devlens.dependency import DependencyAnalyzer
        self.analyzer = DependencyAnalyzer()

    def test_extracts_standard_imports(self):
        tree = _parse(SIMPLE_SOURCE)
        imports = self.analyzer.extract_imports(tree)
        assert "os" in imports
        assert "sys" in imports

    def test_extracts_from_imports(self):
        tree = _parse(SIMPLE_SOURCE)
        imports = self.analyzer.extract_imports(tree)
        assert "pathlib" in imports

    def test_empty_file(self):
        tree = _parse("")
        imports = self.analyzer.extract_imports(tree)
        assert imports == []

    def test_relative_imports(self):
        source = "from . import sibling\nfrom ..pkg import module"
        tree = _parse(source)
        imports = self.analyzer.extract_imports(tree)
        assert ".sibling" in imports or "." in imports


# ---------------------------------------------------------------------------
# CallGraphAnalyzer tests
# ---------------------------------------------------------------------------

class TestCallGraphAnalyzer:
    def setup_method(self):
        from devlens.callgraph import CallGraphAnalyzer
        self.analyzer = CallGraphAnalyzer()

    def test_detects_function_calls(self):
        tree = _parse(SIMPLE_SOURCE)
        graph = self.analyzer.extract_calls(tree)
        assert "shout" in graph
        assert "greet" in graph["shout"]

    def test_empty_function(self):
        source = "def noop(): pass"
        tree = _parse(source)
        graph = self.analyzer.extract_calls(tree)
        assert "noop" in graph
        assert graph["noop"] == []

    def test_method_calls(self):
        source = textwrap.dedent("""\
            def caller():
                obj.method()
                other.nested.call()
        """)
        tree = _parse(source)
        graph = self.analyzer.extract_calls(tree)
        assert "caller" in graph
        callees = graph["caller"]
        assert any("method" in c for c in callees)


# ---------------------------------------------------------------------------
# ComplexityAnalyzer tests
# ---------------------------------------------------------------------------

class TestComplexityAnalyzer:
    def setup_method(self):
        from devlens.complexity import ComplexityAnalyzer
        self.analyzer = ComplexityAnalyzer()

    def test_simple_source(self):
        tree = _parse(SIMPLE_SOURCE)
        metrics = self.analyzer.analyze(tree, SIMPLE_SOURCE)
        assert metrics["num_functions"] >= 2
        assert metrics["num_classes"] >= 1
        assert metrics["lines_of_code"] > 0
        assert "score" in metrics
        assert "grade" in metrics

    def test_complex_source_higher_score(self):
        simple_tree = _parse(SIMPLE_SOURCE)
        complex_tree = _parse(COMPLEX_SOURCE)
        simple_metrics = self.analyzer.analyze(simple_tree, SIMPLE_SOURCE)
        complex_metrics = self.analyzer.analyze(complex_tree, COMPLEX_SOURCE)
        assert complex_metrics["score"] > simple_metrics["score"]

    def test_nesting_depth(self):
        tree = _parse(COMPLEX_SOURCE)
        metrics = self.analyzer.analyze(tree, COMPLEX_SOURCE)
        assert metrics["max_nesting"] >= 3

    def test_grade_a_for_empty(self):
        tree = _parse("x = 1")
        metrics = self.analyzer.analyze(tree, "x = 1")
        assert metrics["grade"].startswith("A")

    def test_loc_excludes_comments(self):
        source = "# comment\n\nx = 1\n# another comment\ny = 2\n"
        tree = _parse(source)
        metrics = self.analyzer.analyze(tree, source)
        assert metrics["lines_of_code"] == 2


# ---------------------------------------------------------------------------
# SecurityScanner tests
# ---------------------------------------------------------------------------

class TestSecurityScanner:
    def setup_method(self):
        from devlens.security import SecurityScanner
        self.scanner = SecurityScanner()

    def test_detects_eval(self):
        tree = _parse(INSECURE_SOURCE)
        issues = self.scanner.scan(tree, INSECURE_SOURCE)
        categories = [i["category"] for i in issues]
        assert "eval()" in categories

    def test_detects_exec(self):
        tree = _parse(INSECURE_SOURCE)
        issues = self.scanner.scan(tree, INSECURE_SOURCE)
        categories = [i["category"] for i in issues]
        assert "exec()" in categories

    def test_detects_shell_true(self):
        tree = _parse(INSECURE_SOURCE)
        issues = self.scanner.scan(tree, INSECURE_SOURCE)
        categories = [i["category"] for i in issues]
        assert "shell=True" in categories

    def test_detects_hardcoded_secret(self):
        tree = _parse(INSECURE_SOURCE)
        issues = self.scanner.scan(tree, INSECURE_SOURCE)
        severities = {i["severity"] for i in issues}
        assert "HIGH" in severities

    def test_clean_source_no_issues(self):
        clean = "def add(a, b):\n    return a + b\n"
        tree = _parse(clean)
        issues = self.scanner.scan(tree, clean)
        assert issues == []

    def test_issues_have_line_numbers(self):
        tree = _parse(INSECURE_SOURCE)
        issues = self.scanner.scan(tree, INSECURE_SOURCE)
        for issue in issues:
            assert issue["line"] > 0


# ---------------------------------------------------------------------------
# ProjectScanner tests
# ---------------------------------------------------------------------------

class TestProjectScanner:
    def test_finds_py_files(self, tmp_path):
        from devlens.analyzer import ProjectScanner
        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "helper.py").write_text("y = 2")

        scanner = ProjectScanner(tmp_path)
        files = scanner.scan()
        names = [f.name for f in files]
        assert "main.py" in names
        assert "helper.py" in names

    def test_ignores_venv(self, tmp_path):
        from devlens.analyzer import ProjectScanner
        (tmp_path / "main.py").write_text("x = 1")
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "ignored.py").write_text("y = 2")

        scanner = ProjectScanner(tmp_path)
        files = scanner.scan()
        paths_str = [str(f) for f in files]
        assert not any(".venv" in p for p in paths_str)

    def test_ignores_pycache(self, tmp_path):
        from devlens.analyzer import ProjectScanner
        (tmp_path / "main.py").write_text("x = 1")
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "cached.pyc").write_text("")

        scanner = ProjectScanner(tmp_path)
        files = scanner.scan()
        assert all(f.suffix == ".py" for f in files)


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_analysis(self, tmp_path):
        from devlens.analyzer import DevLensAnalyzer
        (tmp_path / "app.py").write_text(SIMPLE_SOURCE)
        (tmp_path / "complex.py").write_text(COMPLEX_SOURCE)
        (tmp_path / "insecure.py").write_text(INSECURE_SOURCE)

        analyzer = DevLensAnalyzer(tmp_path)
        report = analyzer.analyze()

        assert report.total_files == 3
        assert report.total_functions > 0
        assert report.total_security_issues > 0
        assert len(report.dependency_graph) == 3
        assert report.avg_complexity > 0
