"""
DevLens - Call Graph Analyzer
Detects function definitions and the functions they call within a Python file.
"""

from __future__ import annotations

import ast
from collections import defaultdict


class CallGraphAnalyzer:
    """
    Builds a per-file call graph by walking the AST.

    For each function defined in a file, records which other
    named functions it calls (direct Name or Attribute calls).
    """

    def extract_calls(self, tree: ast.AST) -> dict[str, list[str]]:
        """
        Extract call relationships from an AST.

        Args:
            tree: Parsed AST of a Python file.

        Returns:
            Dict mapping function_name → list of called function names.
        """
        visitor = _CallVisitor()
        visitor.visit(tree)
        return dict(visitor.graph)


class _CallVisitor(ast.NodeVisitor):
    """AST visitor that builds a function call graph."""

    def __init__(self):
        self.graph: dict[str, list[str]] = defaultdict(list)
        self._current_function: list[str] = []  # Stack for nested functions

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._enter_function(node.name)
        self.generic_visit(node)
        self._exit_function()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._enter_function(node.name)
        self.generic_visit(node)
        self._exit_function()

    def visit_Call(self, node: ast.Call) -> None:
        if self._current_function:
            callee = self._resolve_callee(node.func)
            if callee:
                caller = self._current_function[-1]
                if callee not in self.graph[caller]:
                    self.graph[caller].append(callee)
        self.generic_visit(node)

    def _enter_function(self, name: str) -> None:
        # Use qualified name for nested functions, e.g. outer.inner
        if self._current_function:
            qualified = f"{self._current_function[-1]}.{name}"
        else:
            qualified = name
        self._current_function.append(qualified)
        # Ensure the function appears in the graph even with no calls
        if qualified not in self.graph:
            self.graph[qualified] = []

    def _exit_function(self) -> None:
        self._current_function.pop()

    @staticmethod
    def _resolve_callee(func_node: ast.expr) -> str | None:
        """Extract the name of a called function from its AST node."""
        if isinstance(func_node, ast.Name):
            return func_node.id
        if isinstance(func_node, ast.Attribute):
            # e.g. obj.method → "obj.method"
            obj = _CallVisitor._resolve_callee(func_node.value)
            if obj:
                return f"{obj}.{func_node.attr}"
            return func_node.attr
        return None


def build_networkx_call_graph(
    global_call_graph: dict[str, list[str]],
):
    """
    Convert the global call graph dict to a NetworkX DiGraph.

    Args:
        global_call_graph: Mapping of "file::func" → [callee, ...].

    Returns:
        networkx.DiGraph instance (or None if networkx unavailable).
    """
    try:
        import networkx as nx
    except ImportError:
        return None

    G = nx.DiGraph()
    for caller, callees in global_call_graph.items():
        G.add_node(caller)
        for callee in callees:
            G.add_edge(caller, callee)
    return G
