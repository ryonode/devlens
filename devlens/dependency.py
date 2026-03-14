"""
DevLens - Dependency Analyzer
Extracts import statements and builds a dependency graph between project files.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .analyzer import FileResult


class DependencyAnalyzer:
    """
    Analyzes import statements in Python AST trees.

    Detects:
    - Standard library imports
    - Third-party imports
    - Intra-project (relative and absolute) imports
    """

    def extract_imports(self, tree: ast.AST) -> list[str]:
        """
        Extract all import names from an AST.

        Args:
            tree: Parsed AST of a Python file.

        Returns:
            Sorted list of imported module names.
        """
        imports: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                level = node.level  # dots for relative imports
                prefix = "." * level
                imports.append(f"{prefix}{module}" if module else prefix)

        return sorted(set(imports))

    def build_project_graph(
        self,
        files: list["FileResult"],
        root: Path,
    ) -> dict[str, list[str]]:
        """
        Build a dependency graph mapping file → list of imported modules.

        Attempts to resolve intra-project imports to relative file paths
        where possible; falls back to the raw module name.

        Args:
            files: List of analyzed file results.
            root: Project root directory.

        Returns:
            Dict mapping relative file path → list of dependencies.
        """
        # Build a lookup of module path → relative file path
        module_map = self._build_module_map(files, root)

        graph: dict[str, list[str]] = {}

        for file_result in files:
            deps: list[str] = []
            for imp in file_result.imports:
                resolved = self._resolve_import(imp, file_result.relative_path, module_map)
                deps.append(resolved)
            graph[file_result.relative_path] = sorted(set(deps))

        return graph

    @staticmethod
    def _build_module_map(files: list["FileResult"], root: Path) -> dict[str, str]:
        """Map dotted module names to relative file paths."""
        module_map: dict[str, str] = {}
        for f in files:
            # Convert path to dotted module name, e.g. devlens/cli.py → devlens.cli
            rel = Path(f.relative_path)
            parts = list(rel.with_suffix("").parts)
            if parts and parts[-1] == "__init__":
                parts = parts[:-1]
            dotted = ".".join(parts)
            module_map[dotted] = f.relative_path
        return module_map

    @staticmethod
    def _resolve_import(
        imp: str,
        current_file: str,
        module_map: dict[str, str],
    ) -> str:
        """
        Attempt to resolve an import to a project-internal file path.
        Falls back to the raw import string if not resolvable.
        """
        # Strip leading dots for relative imports
        clean = imp.lstrip(".")

        if clean in module_map:
            return module_map[clean]

        # Try prefix match (e.g. "devlens.cli" matches "devlens/cli.py")
        for mod, path in module_map.items():
            if clean == mod or clean.startswith(mod + "."):
                return path

        return imp  # External or unresolvable import


def format_dependency_table(graph: dict[str, list[str]]) -> list[tuple[str, str, int]]:
    """
    Flatten dependency graph into rows suitable for tabular display.

    Returns:
        List of (source_file, dependency, dependency_count) tuples.
    """
    rows = []
    for source, deps in sorted(graph.items()):
        for dep in deps:
            rows.append((source, dep, len(deps)))
    return rows
