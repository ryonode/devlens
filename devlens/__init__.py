"""
DevLens – Instant Python codebase intelligence.
"""

__version__ = "0.1.0"
__author__ = "DevLens Contributors"
__license__ = "MIT"

from .analyzer import DevLensAnalyzer, ProjectReport, FileResult, ProjectScanner
from .dependency import DependencyAnalyzer
from .callgraph import CallGraphAnalyzer
from .complexity import ComplexityAnalyzer
from .security import SecurityScanner

__all__ = [
    "DevLensAnalyzer",
    "ProjectReport",
    "FileResult",
    "ProjectScanner",
    "DependencyAnalyzer",
    "CallGraphAnalyzer",
    "ComplexityAnalyzer",
    "SecurityScanner",
]
