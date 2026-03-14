"""
DevLens - Graph Visualization
Renders dependency and call graphs using NetworkX + Matplotlib.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .analyzer import ProjectReport


def render_dependency_graph(
    report: "ProjectReport",
    output_path: str | Path = "devlens_dependency.png",
    max_nodes: int = 40,
) -> Path:
    """
    Render the project's file dependency graph as a PNG image.

    Args:
        report:      Full project analysis report.
        output_path: Where to save the image.
        max_nodes:   Cap node count for readability.

    Returns:
        Path to the saved image file.
    """
    try:
        import networkx as nx
        import matplotlib
        matplotlib.use("Agg")  # headless backend
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise RuntimeError(
            f"Missing required library: {e}. Install with: pip install networkx matplotlib"
        ) from e

    G = nx.DiGraph()

    # Add edges from dependency graph
    for source, deps in report.dependency_graph.items():
        src_label = _shorten_label(source)
        G.add_node(src_label)
        for dep in deps:
            dep_label = _shorten_label(dep)
            G.add_edge(src_label, dep_label)

    # Trim to max_nodes most-connected nodes
    if len(G.nodes) > max_nodes:
        top = sorted(G.nodes, key=lambda n: G.degree(n), reverse=True)[:max_nodes]
        G = G.subgraph(top).copy()

    _save_graph(
        G,
        output_path=output_path,
        title="DevLens – File Dependency Graph",
        node_color="#4C9BE8",
        edge_color="#888888",
    )
    return Path(output_path)


def render_call_graph(
    report: "ProjectReport",
    output_path: str | Path = "devlens_callgraph.png",
    max_nodes: int = 50,
) -> Path:
    """
    Render the global function call graph as a PNG image.

    Args:
        report:      Full project analysis report.
        output_path: Where to save the image.
        max_nodes:   Cap node count for readability.

    Returns:
        Path to the saved image file.
    """
    try:
        import networkx as nx
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise RuntimeError(
            f"Missing required library: {e}. Install with: pip install networkx matplotlib"
        ) from e

    G = nx.DiGraph()

    for caller, callees in report.global_call_graph.items():
        caller_label = _shorten_label(caller, max_len=25)
        G.add_node(caller_label)
        for callee in callees:
            callee_label = _shorten_label(callee, max_len=25)
            G.add_edge(caller_label, callee_label)

    # Trim to most connected
    if len(G.nodes) > max_nodes:
        top = sorted(G.nodes, key=lambda n: G.degree(n), reverse=True)[:max_nodes]
        G = G.subgraph(top).copy()

    _save_graph(
        G,
        output_path=output_path,
        title="DevLens – Function Call Graph",
        node_color="#E87B4C",
        edge_color="#AAAAAA",
    )
    return Path(output_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _shorten_label(label: str, max_len: int = 30) -> str:
    """Shorten a long path/label for graph readability."""
    if len(label) <= max_len:
        return label
    # Show last N chars with ellipsis prefix
    return "…" + label[-(max_len - 1):]


def _save_graph(
    G,
    output_path: str | Path,
    title: str,
    node_color: str,
    edge_color: str,
) -> None:
    """Layout and save a NetworkX graph using matplotlib."""
    import networkx as nx
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(16, 10), dpi=120)
    fig.patch.set_facecolor("#1e1e2e")
    ax.set_facecolor("#1e1e2e")

    if len(G.nodes) == 0:
        ax.text(
            0.5, 0.5, "No data to display",
            ha="center", va="center",
            color="white", fontsize=14,
            transform=ax.transAxes,
        )
        ax.set_title(title, color="white", fontsize=14, pad=15)
        plt.tight_layout()
        plt.savefig(output_path, facecolor=fig.get_facecolor())
        plt.close(fig)
        return

    # Choose layout based on graph size
    if len(G.nodes) <= 10:
        pos = nx.spring_layout(G, seed=42, k=2.0)
    elif len(G.nodes) <= 25:
        pos = nx.kamada_kawai_layout(G)
    else:
        pos = nx.spring_layout(G, seed=42, k=1.5, iterations=50)

    # Node sizes based on degree
    degrees = dict(G.degree())
    node_sizes = [max(500, degrees.get(n, 1) * 200) for n in G.nodes]

    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_color,
        node_size=node_sizes,
        alpha=0.85,
    )
    nx.draw_networkx_labels(
        G, pos, ax=ax,
        font_size=6,
        font_color="white",
        font_weight="bold",
    )
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color=edge_color,
        arrows=True,
        arrowsize=12,
        alpha=0.6,
        connectionstyle="arc3,rad=0.1",
    )

    ax.set_title(title, color="white", fontsize=14, pad=15, fontweight="bold")
    ax.axis("off")

    # Legend: node count
    legend_text = f"{len(G.nodes)} nodes  ·  {len(G.edges)} edges"
    ax.text(
        0.01, 0.01, legend_text,
        transform=ax.transAxes,
        color="#aaaaaa", fontsize=8,
    )

    plt.tight_layout()
    plt.savefig(output_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
