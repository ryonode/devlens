"""
DevLens – Entry point.

Usage:
    python main.py analyze ./myproject
    python main.py graph ./myproject --output ./graphs
    python main.py complexity ./myproject
    python main.py security ./myproject
"""

from devlens.cli import main

if __name__ == "__main__":
    main()
