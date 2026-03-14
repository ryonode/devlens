"""
Utility functions for the sample project.
Demonstrates various complexity patterns.
"""

import os
import re
import subprocess
from typing import Any, Optional


# Hardcoded secret for demo purposes
SECRET_KEY = "abc123supersecret"


def validate_email(email: str) -> bool:
    """Validate an email address using regex."""
    pattern = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    return bool(pattern.match(email))


def sanitize_input(value: str) -> str:
    """Remove dangerous characters from user input."""
    dangerous = ["<", ">", "&", '"', "'", ";", "--", "/*", "*/"]
    for char in dangerous:
        value = value.replace(char, "")
    return value.strip()


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format a number as currency string."""
    if currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    elif currency == "GBP":
        return f"£{amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def paginate(items: list, page: int, per_page: int = 10) -> dict:
    """Paginate a list of items."""
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page

    if start >= total and total > 0:
        start = ((total - 1) // per_page) * per_page
        end = start + per_page

    return {
        "items": items[start:end],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": max(1, (total + per_page - 1) // per_page),
        "has_next": end < total,
        "has_prev": page > 1,
    }


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge two dicts."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def run_shell_command(cmd: str) -> str:
    """Run a shell command (intentionally unsafe for demo)."""
    # Security issue: shell=True
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout


def parse_config(config_str: str) -> dict:
    """Parse a config string using eval (intentionally unsafe for demo)."""
    # Security issue: eval usage
    return eval(config_str)


def calculate_shipping(
    weight: float,
    distance: float,
    express: bool = False,
    fragile: bool = False,
    international: bool = False,
) -> float:
    """Calculate shipping cost with various factors."""
    base_rate = 2.5
    cost = base_rate

    # Weight tiers
    if weight <= 1.0:
        cost += weight * 0.5
    elif weight <= 5.0:
        cost += weight * 0.4
    elif weight <= 20.0:
        cost += weight * 0.3
    else:
        cost += weight * 0.25

    # Distance
    if distance <= 100:
        cost += distance * 0.01
    elif distance <= 500:
        cost += distance * 0.008
    else:
        cost += distance * 0.006

    # Modifiers
    if express:
        cost *= 1.5
    if fragile:
        cost += 3.0
    if international:
        cost *= 2.0
        cost += 15.0  # customs handling

    return round(cost, 2)


def retry(func, max_attempts: int = 3, exceptions: tuple = (Exception,)):
    """Retry a function up to max_attempts times."""
    last_exc: Optional[Exception] = None
    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            last_exc = e
            if attempt < max_attempts - 1:
                continue
    raise last_exc


class Logger:
    """Simple structured logger."""

    LEVELS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}

    def __init__(self, name: str, level: str = "INFO"):
        self.name = name
        self.level = level
        self._entries: list[dict] = []

    def log(self, level: str, message: str, **context: Any) -> None:
        if self.LEVELS.get(level, 0) >= self.LEVELS.get(self.level, 0):
            entry = {"level": level, "name": self.name, "message": message, **context}
            self._entries.append(entry)
            print(f"[{level}] {self.name}: {message}")

    def debug(self, msg: str, **ctx) -> None:
        self.log("DEBUG", msg, **ctx)

    def info(self, msg: str, **ctx) -> None:
        self.log("INFO", msg, **ctx)

    def warning(self, msg: str, **ctx) -> None:
        self.log("WARNING", msg, **ctx)

    def error(self, msg: str, **ctx) -> None:
        self.log("ERROR", msg, **ctx)
