"""
DevLens - Complexity Analyzer
Computes code complexity metrics from Python AST trees.

Metrics computed:
  - num_functions:   total function/method definitions
  - num_classes:     total class definitions
  - num_conditionals: if / elif / ternary expressions
  - num_loops:       for / while loops
  - max_nesting:     maximum nesting depth of control structures
  - lines_of_code:   non-blank, non-comment source lines
  - score:           composite complexity score (higher = more complex)
"""

from __future__ import annotations

import ast


# Weights for composite score
_WEIGHTS = {
    "num_functions": 1,
    "num_classes": 1,
    "num_conditionals": 2,
    "num_loops": 2,
    "max_nesting": 5,
}


class ComplexityAnalyzer:
    """Analyzes code complexity from an AST."""

    def analyze(self, tree: ast.AST, source: str) -> dict:
        """
        Compute all complexity metrics for a parsed file.

        Args:
            tree:   Parsed AST.
            source: Raw source text (used for LOC count).

        Returns:
            Dict with individual metrics and a composite ``score``.
        """
        metrics = {
            "num_functions": 0,
            "num_classes": 0,
            "num_conditionals": 0,
            "num_loops": 0,
            "max_nesting": 0,
            "lines_of_code": _count_loc(source),
        }

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["num_functions"] += 1
            elif isinstance(node, ast.ClassDef):
                metrics["num_classes"] += 1
            elif isinstance(node, (ast.If, ast.IfExp)):
                metrics["num_conditionals"] += 1
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
                metrics["num_loops"] += 1

        metrics["max_nesting"] = _max_nesting_depth(tree)
        metrics["score"] = _compute_score(metrics)
        metrics["grade"] = _grade(metrics["score"])

        return metrics


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_loc(source: str) -> int:
    """Count non-blank, non-comment lines."""
    count = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def _max_nesting_depth(tree: ast.AST) -> int:
    """Return the maximum nesting depth of control flow nodes."""
    _NESTING_NODES = (
        ast.If, ast.For, ast.AsyncFor, ast.While,
        ast.With, ast.AsyncWith, ast.Try,
        ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
    )
    visitor = _NestingVisitor(_NESTING_NODES)
    visitor.visit(tree)
    return visitor.max_depth


class _NestingVisitor(ast.NodeVisitor):
    def __init__(self, nesting_nodes: tuple):
        self._nesting_nodes = nesting_nodes
        self._depth = 0
        self.max_depth = 0

    def visit(self, node: ast.AST) -> None:
        if isinstance(node, self._nesting_nodes):
            self._depth += 1
            self.max_depth = max(self.max_depth, self._depth)
            self.generic_visit(node)
            self._depth -= 1
        else:
            self.generic_visit(node)


def _compute_score(metrics: dict) -> int:
    """Compute a weighted composite complexity score."""
    score = 0
    for key, weight in _WEIGHTS.items():
        score += metrics.get(key, 0) * weight
    return score


def _grade(score: int) -> str:
    """Convert numeric score to a human-readable grade."""
    if score <= 10:
        return "A (Simple)"
    elif score <= 25:
        return "B (Moderate)"
    elif score <= 50:
        return "C (Complex)"
    elif score <= 100:
        return "D (Very Complex)"
    else:
        return "F (Extremely Complex)"
