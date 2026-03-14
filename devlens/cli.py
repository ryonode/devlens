"""
DevLens - CLI Interface
Professional command-line interface built with Typer + Rich.

Commands:
  devlens analyze    Full codebase analysis with summary dashboard
  devlens graph      Generate dependency/call graph visualizations
  devlens complexity Per-file complexity report
  devlens security   Security vulnerability scan
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.rule import Rule

from .analyzer import DevLensAnalyzer, ProjectReport
from .security import SEVERITY_COLORS

app = typer.Typer(
    name="devlens",
    help="[bold cyan]DevLens[/bold cyan] – Instant Python codebase intelligence.",
    rich_markup_mode="rich",
    add_completion=False,
)

console = Console()

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _load_report(path: str) -> ProjectReport:
    """Run analysis and return the report, exiting on error."""
    target = Path(path).resolve()
    if not target.exists():
        console.print(f"[red]✗ Path not found:[/red] {path}")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]DevLens[/bold cyan] analyzing [green]{target}[/green]\n")

    try:
        analyzer = DevLensAnalyzer(target)
        return analyzer.analyze()
    except Exception as exc:
        console.print(f"[red]Analysis failed:[/red] {exc}")
        raise typer.Exit(1)


def _print_header(title: str) -> None:
    console.print(Rule(f"[bold cyan]{title}[/bold cyan]", style="cyan"))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def analyze(
    path: str = typer.Argument(".", help="Path to the Python project directory."),
    show_imports: bool = typer.Option(False, "--imports", "-i", help="Show per-file import list."),
):
    """
    [bold]Full project analysis[/bold] – dependencies, complexity, and security summary.
    """
    report = _load_report(path)

    # ── Summary cards ────────────────────────────────────────────────────────
    _print_header("Project Summary")

    cards = [
        Panel(
            f"[bold white]{report.total_files}[/bold white]\n[dim]Python Files[/dim]",
            border_style="cyan", expand=True,
        ),
        Panel(
            f"[bold white]{report.total_functions}[/bold white]\n[dim]Functions[/dim]",
            border_style="green", expand=True,
        ),
        Panel(
            f"[bold white]{report.total_classes}[/bold white]\n[dim]Classes[/dim]",
            border_style="blue", expand=True,
        ),
        Panel(
            f"[bold white]{report.avg_complexity}[/bold white]\n[dim]Avg Complexity[/dim]",
            border_style="yellow", expand=True,
        ),
        Panel(
            f"[bold {'red' if report.total_security_issues else 'green'}]{report.total_security_issues}[/bold {'red' if report.total_security_issues else 'green'}]\n[dim]Security Issues[/dim]",
            border_style="red" if report.total_security_issues else "green", expand=True,
        ),
    ]
    console.print(Columns(cards, equal=True, expand=True))

    # ── File list ────────────────────────────────────────────────────────────
    console.print()
    _print_header("Files Analyzed")

    tbl = Table(
        "File", "Functions", "Classes", "Complexity", "Grade", "Issues",
        box=box.ROUNDED, header_style="bold cyan", show_lines=False,
    )

    for fr in sorted(report.files, key=lambda f: f.relative_path):
        if fr.parse_error:
            tbl.add_row(
                f"[red]{fr.relative_path}[/red]",
                "[dim]–[/dim]", "[dim]–[/dim]",
                "[dim]–[/dim]", "[dim]PARSE ERROR[/dim]",
                "[dim]–[/dim]",
            )
            continue

        score = fr.complexity.get("score", 0)
        grade = fr.complexity.get("grade", "–")
        grade_color = _grade_color(grade)

        tbl.add_row(
            fr.relative_path,
            str(len(fr.functions)),
            str(len(fr.classes)),
            str(score),
            f"[{grade_color}]{grade}[/{grade_color}]",
            _issues_badge(len(fr.security_issues)),
        )

    console.print(tbl)

    # ── Per-file imports (optional) ──────────────────────────────────────────
    if show_imports:
        console.print()
        _print_header("Imports per File")
        for fr in report.files:
            if fr.imports:
                console.print(f"\n[bold]{fr.relative_path}[/bold]")
                for imp in fr.imports:
                    console.print(f"  [dim]•[/dim] {imp}")

    console.print()
    console.print("[dim]Tip: run [bold]devlens security[/bold], [bold]devlens complexity[/bold], or [bold]devlens graph[/bold] for details.[/dim]\n")


@app.command()
def complexity(
    path: str = typer.Argument(".", help="Path to the Python project directory."),
    top: int = typer.Option(20, "--top", "-n", help="Show top N most complex files."),
    min_score: int = typer.Option(0, "--min-score", help="Only show files with score ≥ N."),
):
    """
    [bold]Complexity report[/bold] – detailed metrics for every Python file.
    """
    report = _load_report(path)

    _print_header("Complexity Analysis")

    files = [f for f in report.files if not f.parse_error]
    files = [f for f in files if f.complexity.get("score", 0) >= min_score]
    files = sorted(files, key=lambda f: f.complexity.get("score", 0), reverse=True)[:top]

    tbl = Table(
        "File", "LOC", "Functions", "Classes",
        "Conditionals", "Loops", "Max Nesting", "Score", "Grade",
        box=box.SIMPLE_HEAD, header_style="bold cyan", show_lines=True,
    )

    for fr in files:
        c = fr.complexity
        grade = c.get("grade", "–")
        tbl.add_row(
            fr.relative_path,
            str(c.get("lines_of_code", 0)),
            str(c.get("num_functions", 0)),
            str(c.get("num_classes", 0)),
            str(c.get("num_conditionals", 0)),
            str(c.get("num_loops", 0)),
            str(c.get("max_nesting", 0)),
            f"[bold]{c.get('score', 0)}[/bold]",
            f"[{_grade_color(grade)}]{grade}[/{_grade_color(grade)}]",
        )

    console.print(tbl)
    console.print(f"\n[dim]Showing top {len(files)} of {report.total_files} files.[/dim]\n")


@app.command()
def security(
    path: str = typer.Argument(".", help="Path to the Python project directory."),
    severity: Optional[str] = typer.Option(
        None, "--severity", "-s",
        help="Filter by severity: HIGH / MEDIUM / LOW",
    ),
):
    """
    [bold]Security scan[/bold] – detect risky patterns in your codebase.
    """
    report = _load_report(path)

    _print_header("Security Scan")

    all_issues = []
    for fr in report.files:
        all_issues.extend(fr.security_issues)

    if severity:
        all_issues = [i for i in all_issues if i["severity"].upper() == severity.upper()]

    if not all_issues:
        console.print("[bold green]✔  No security issues detected![/bold green]\n")
        return

    # Summary counts
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for issue in all_issues:
        counts[issue["severity"]] = counts.get(issue["severity"], 0) + 1

    summary_cards = []
    for sev, count in counts.items():
        color = SEVERITY_COLORS.get(sev, "white")
        summary_cards.append(
            Panel(
                f"[{color}]{count}[/{color}]\n[dim]{sev}[/dim]",
                border_style=color.replace("bold ", ""),
                expand=True,
            )
        )
    console.print(Columns(summary_cards, equal=True, expand=True))
    console.print()

    # Issue table
    tbl = Table(
        "Severity", "Category", "File", "Line", "Description",
        box=box.ROUNDED, header_style="bold cyan", show_lines=True,
    )

    for issue in sorted(all_issues, key=lambda i: (
        ["HIGH", "MEDIUM", "LOW"].index(i["severity"]),
        i["file"],
        i["line"],
    )):
        sev = issue["severity"]
        color = SEVERITY_COLORS.get(sev, "white")
        tbl.add_row(
            f"[{color}]{sev}[/{color}]",
            issue["category"],
            issue["file"],
            str(issue["line"]),
            issue["message"],
        )

    console.print(tbl)
    console.print(f"\n[dim]Total: {len(all_issues)} issue(s) found.[/dim]\n")


@app.command()
def graph(
    path: str = typer.Argument(".", help="Path to the Python project directory."),
    output: str = typer.Option(".", "--output", "-o", help="Output directory for PNG files."),
    kind: str = typer.Option(
        "both", "--kind", "-k",
        help="Graph type: deps | calls | both",
    ),
):
    """
    [bold]Graph visualization[/bold] – render dependency and call graphs as PNG images.
    """
    from .graph import render_dependency_graph, render_call_graph

    report = _load_report(path)
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)

    _print_header("Graph Visualization")

    if kind in ("deps", "both"):
        dep_path = out_dir / "devlens_dependency.png"
        try:
            result = render_dependency_graph(report, dep_path)
            console.print(f"[green]✔[/green]  Dependency graph saved → [bold]{result}[/bold]")
        except RuntimeError as e:
            console.print(f"[yellow]⚠[/yellow]  Could not render dependency graph: {e}")

    if kind in ("calls", "both"):
        call_path = out_dir / "devlens_callgraph.png"
        try:
            result = render_call_graph(report, call_path)
            console.print(f"[green]✔[/green]  Call graph saved → [bold]{result}[/bold]")
        except RuntimeError as e:
            console.print(f"[yellow]⚠[/yellow]  Could not render call graph: {e}")

    console.print()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _grade_color(grade: str) -> str:
    if grade.startswith("A"):
        return "green"
    elif grade.startswith("B"):
        return "cyan"
    elif grade.startswith("C"):
        return "yellow"
    elif grade.startswith("D"):
        return "red"
    elif grade.startswith("F"):
        return "bold red"
    return "white"


def _issues_badge(count: int) -> str:
    if count == 0:
        return "[green]0[/green]"
    elif count <= 2:
        return f"[yellow]{count}[/yellow]"
    else:
        return f"[bold red]{count}[/bold red]"


def main() -> None:
    app()


if __name__ == "__main__":
    main()
