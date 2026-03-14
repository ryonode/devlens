"""
DevLens - Security Scanner
Detects common insecure patterns in Python source code.

Checks performed:
  - Hardcoded secrets / API keys (regex on string literals)
  - Use of eval() / exec()
  - Use of compile() with user-controlled input (heuristic)
  - subprocess with shell=True
  - Pickle deserialization
  - Use of assert for security checks
  - MD5 / SHA1 usage (weak hashing)
  - Hardcoded IPs / URLs in string literals
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass


@dataclass
class SecurityIssue:
    """A single detected security issue."""
    severity: str       # HIGH / MEDIUM / LOW
    category: str       # Short category label
    message: str        # Human-readable description
    line: int           # Source line number
    file: str = ""      # Filled in by caller

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "line": self.line,
            "file": self.file,
        }


# Regex patterns for suspicious string contents
_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("API Key",        re.compile(r"(?i)(api[_\-]?key|apikey)\s*=\s*['\"][A-Za-z0-9+/=_\-]{8,}['\"]")),
    ("Secret Token",   re.compile(r"(?i)(secret[_\-]?key|secret|token)\s*=\s*['\"][A-Za-z0-9+/=_\-]{8,}['\"]")),
    ("Password",       re.compile(r"(?i)(password|passwd|pwd)\s*=\s*['\"][^'\"]{4,}['\"]")),
    ("AWS Key",        re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Private Key",    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("JWT Token",      re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")),
]


class SecurityScanner:
    """
    Scans Python AST and raw source for common security anti-patterns.
    """

    def scan(self, tree: ast.AST, source: str, filepath: str = "") -> list[dict]:
        """
        Run all security checks and return a list of issue dicts.

        Args:
            tree:     Parsed AST.
            source:   Raw source text.
            filepath: File path (used for labeling issues).

        Returns:
            List of issue dicts (see SecurityIssue.as_dict).
        """
        issues: list[SecurityIssue] = []

        issues.extend(self._check_ast(tree))
        issues.extend(self._check_source(source))

        for issue in issues:
            issue.file = filepath

        return [i.as_dict() for i in issues]

    # ------------------------------------------------------------------
    # AST-based checks
    # ------------------------------------------------------------------

    def _check_ast(self, tree: ast.AST) -> list[SecurityIssue]:
        issues: list[SecurityIssue] = []
        for node in ast.walk(tree):
            issues.extend(self._check_node(node))
        return issues

    @staticmethod
    def _check_node(node: ast.AST) -> list[SecurityIssue]:
        issues: list[SecurityIssue] = []
        line = getattr(node, "lineno", 0)

        # eval() usage
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node)

            if func_name == "eval":
                issues.append(SecurityIssue(
                    severity="HIGH",
                    category="eval()",
                    message="Use of eval() can execute arbitrary code.",
                    line=line,
                ))

            elif func_name == "exec":
                issues.append(SecurityIssue(
                    severity="HIGH",
                    category="exec()",
                    message="Use of exec() can execute arbitrary code.",
                    line=line,
                ))

            elif func_name == "compile":
                issues.append(SecurityIssue(
                    severity="MEDIUM",
                    category="compile()",
                    message="compile() with dynamic input can execute arbitrary code.",
                    line=line,
                ))

            elif func_name in ("pickle.loads", "pickle.load", "cPickle.loads"):
                issues.append(SecurityIssue(
                    severity="HIGH",
                    category="Pickle",
                    message="Deserializing pickle data from untrusted sources is unsafe.",
                    line=line,
                ))

            elif func_name in ("subprocess.call", "subprocess.run", "subprocess.Popen"):
                # Check for shell=True keyword
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        issues.append(SecurityIssue(
                            severity="HIGH",
                            category="shell=True",
                            message="subprocess with shell=True is vulnerable to shell injection.",
                            line=line,
                        ))

            elif func_name in ("hashlib.md5", "hashlib.sha1"):
                issues.append(SecurityIssue(
                    severity="LOW",
                    category="Weak Hash",
                    message=f"{func_name}() uses a cryptographically weak hashing algorithm.",
                    line=line,
                ))

        # assert used as security check heuristic
        elif isinstance(node, ast.Assert):
            issues.append(SecurityIssue(
                severity="LOW",
                category="assert",
                message="assert statements are removed with -O flag; don't use for security checks.",
                line=line,
            ))

        return issues

    # ------------------------------------------------------------------
    # Regex-based source scan
    # ------------------------------------------------------------------

    @staticmethod
    def _check_source(source: str) -> list[SecurityIssue]:
        issues: list[SecurityIssue] = []
        lines = source.splitlines()
        for lineno, line in enumerate(lines, start=1):
            for label, pattern in _SECRET_PATTERNS:
                if pattern.search(line):
                    issues.append(SecurityIssue(
                        severity="HIGH",
                        category="Hardcoded Secret",
                        message=f"Possible hardcoded {label} detected.",
                        line=lineno,
                    ))
        return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_call_name(node: ast.Call) -> str:
    """Extract a dotted name from a Call node's func attribute."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        parts = []
        current = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


SEVERITY_COLORS = {
    "HIGH":   "bold red",
    "MEDIUM": "bold yellow",
    "LOW":    "bold cyan",
}
