"""
DevLens Desktop GUI
High-quality, crisp desktop application built with tkinter.
Run: python devlens_gui.py
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog
import platform

# ── Fix blurry rendering on Windows (MUST be before Tk() is created) ────────
if platform.system() == "Windows":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(2)   # Per-monitor DPI aware
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devlens.analyzer import DevLensAnalyzer

# ── Palette ──────────────────────────────────────────────────────────────────
C = {
    "bg":       "#0d1117",
    "surface":  "#161b22",
    "panel":    "#1c2333",
    "border":   "#30363d",
    "accent":   "#58a6ff",
    "green":    "#3fb950",
    "yellow":   "#d29922",
    "orange":   "#db6d28",
    "red":      "#f85149",
    "text":     "#e6edf3",
    "muted":    "#8b949e",
    "dim":      "#484f58",
    "select":   "#1f6feb",
}

FONT_MONO = ("Consolas",  10)
FONT_MONO_SM = ("Consolas", 9)
FONT_MONO_LG = ("Consolas", 13, "bold")
FONT_UI   = ("Segoe UI",  10)
FONT_UI_B = ("Segoe UI",  10, "bold")
FONT_UI_LG = ("Segoe UI", 18, "bold")
FONT_UI_XL = ("Segoe UI", 28, "bold")

# Fall back to system mono on non-Windows
if platform.system() == "Darwin":
    FONT_MONO    = ("Menlo",   10)
    FONT_MONO_SM = ("Menlo",   9)
    FONT_MONO_LG = ("Menlo",   13, "bold")
    FONT_UI      = ("SF Pro Display", 10)
    FONT_UI_B    = ("SF Pro Display", 10, "bold")
    FONT_UI_LG   = ("SF Pro Display", 18, "bold")
    FONT_UI_XL   = ("SF Pro Display", 28, "bold")
elif platform.system() == "Linux":
    FONT_MONO    = ("DejaVu Sans Mono", 10)
    FONT_MONO_SM = ("DejaVu Sans Mono", 9)
    FONT_MONO_LG = ("DejaVu Sans Mono", 11, "bold")


class DevLensApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # ── Window setup ─────────────────────────────────────────────────────
        self.title("DevLens")
        self.configure(bg=C["bg"])
        self.geometry("1200x820")
        self.minsize(960, 640)

        # Sharp icon (simple colored square as fallback)
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        # Enable crisp font rendering on Windows
        if platform.system() == "Windows":
            self.tk.call("tk", "scaling", self.winfo_fpixels("1i") / 72.0)

        self._report = None
        self._path_var = tk.StringVar()

        self._setup_styles()
        self._build_layout()

    # ── ttk styles ────────────────────────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")

        # Notebook
        s.configure("D.TNotebook",
            background=C["surface"], borderwidth=0, tabmargins=0)
        s.configure("D.TNotebook.Tab",
            background=C["panel"], foreground=C["muted"],
            padding=[18, 8], font=FONT_UI_B,
            borderwidth=0, relief="flat")
        s.map("D.TNotebook.Tab",
            background=[("selected", C["bg"]), ("active", C["border"])],
            foreground=[("selected", C["accent"]), ("active", C["text"])])

        # Treeview
        s.configure("D.Treeview",
            background=C["surface"], foreground=C["text"],
            fieldbackground=C["surface"], borderwidth=0,
            font=FONT_MONO_SM, rowheight=30)
        s.configure("D.Treeview.Heading",
            background=C["panel"], foreground=C["muted"],
            font=("Segoe UI", 9, "bold") if platform.system()=="Windows" else FONT_UI_B,
            relief="flat", borderwidth=0)
        s.map("D.Treeview",
            background=[("selected", C["select"])],
            foreground=[("selected", C["text"])])

        # Scrollbar
        s.configure("D.Vertical.TScrollbar",
            background=C["panel"], troughcolor=C["surface"],
            borderwidth=0, relief="flat", arrowsize=14)
        s.map("D.Vertical.TScrollbar",
            background=[("active", C["border"]), ("disabled", C["dim"])])

        # Progressbar
        s.configure("D.Horizontal.TProgressbar",
            background=C["accent"], troughcolor=C["panel"],
            borderwidth=0, thickness=3)

        # Separator
        s.configure("D.TSeparator", background=C["border"])

    # ── Main layout ───────────────────────────────────────────────────────────
    def _build_layout(self):
        # ── Sidebar ──────────────────────────────────────────────────────────
        sidebar = tk.Frame(self, bg=C["surface"], width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo area
        logo_frame = tk.Frame(sidebar, bg=C["surface"], pady=0)
        logo_frame.pack(fill="x")

        # Accent top bar
        tk.Frame(logo_frame, bg=C["accent"], height=3).pack(fill="x")

        tk.Label(logo_frame, text="🔍", bg=C["surface"], fg=C["accent"],
                 font=("Segoe UI", 26)).pack(pady=(20, 4))
        tk.Label(logo_frame, text="DevLens", bg=C["surface"], fg=C["text"],
                 font=FONT_UI_LG).pack()
        tk.Label(logo_frame, text="Codebase Intelligence", bg=C["surface"],
                 fg=C["muted"], font=FONT_MONO_SM).pack(pady=(2, 20))

        tk.Frame(sidebar, bg=C["border"], height=1).pack(fill="x", padx=16)

        # Nav buttons
        self._nav_btns = {}
        nav_items = [
            ("summary",    "⬜  Summary"),
            ("complexity", "📊  Complexity"),
            ("security",   "🔒  Security"),
            ("deps",       "🔗  Dependencies"),
            ("calls",      "📞  Call Graph"),
        ]
        nav_frame = tk.Frame(sidebar, bg=C["surface"])
        nav_frame.pack(fill="x", pady=12)

        for key, label in nav_items:
            btn = tk.Button(
                nav_frame, text=label,
                bg=C["surface"], fg=C["muted"],
                activebackground=C["panel"], activeforeground=C["accent"],
                relief="flat", anchor="w",
                font=FONT_UI, padx=20, pady=10,
                cursor="hand2", bd=0,
                command=lambda k=key: self._show_panel(k),
            )
            btn.pack(fill="x")
            self._nav_btns[key] = btn

        # Stats in sidebar
        tk.Frame(sidebar, bg=C["border"], height=1).pack(fill="x", padx=16, pady=(8,0))
        self._stat_frame = tk.Frame(sidebar, bg=C["surface"])
        self._stat_frame.pack(fill="x", padx=16, pady=16)

        self._stat_vars = {}
        stat_defs = [
            ("files",    "Files"),
            ("funcs",    "Functions"),
            ("classes",  "Classes"),
            ("cx",       "Avg Complexity"),
            ("issues",   "Security Issues"),
        ]
        for key, label in stat_defs:
            row = tk.Frame(self._stat_frame, bg=C["surface"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, bg=C["surface"], fg=C["muted"],
                     font=FONT_MONO_SM, anchor="w").pack(side="left")
            v = tk.StringVar(value="—")
            self._stat_vars[key] = v
            tk.Label(row, textvariable=v, bg=C["surface"], fg=C["accent"],
                     font=("Consolas", 10, "bold"), anchor="e").pack(side="right")

        # Sidebar bottom
        tk.Frame(sidebar, bg=C["border"], height=1).pack(fill="x", padx=16, side="bottom", pady=8)
        tk.Label(sidebar, text="v0.1.0  •  MIT License", bg=C["surface"],
                 fg=C["dim"], font=FONT_MONO_SM).pack(side="bottom", pady=8)

        # ── Main content area ─────────────────────────────────────────────────
        main = tk.Frame(self, bg=C["bg"])
        main.pack(side="right", fill="both", expand=True)

        # Top bar: folder picker
        topbar = tk.Frame(main, bg=C["surface"], pady=0)
        topbar.pack(fill="x")
        tk.Frame(topbar, bg=C["border"], height=1).pack(fill="x", side="bottom")

        picker = tk.Frame(topbar, bg=C["surface"], padx=20, pady=14)
        picker.pack(fill="x")

        tk.Label(picker, text="PROJECT", bg=C["surface"], fg=C["muted"],
                 font=("Consolas", 8, "bold")).pack(side="left", padx=(0, 10))

        # Path entry with border frame
        entry_border = tk.Frame(picker, bg=C["border"], padx=1, pady=1)
        entry_border.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._path_entry = tk.Entry(
            entry_border, textvariable=self._path_var,
            bg=C["panel"], fg=C["text"],
            insertbackground=C["accent"],
            relief="flat", font=FONT_MONO,
            bd=0,
        )
        self._path_entry.pack(fill="x", ipady=7, ipadx=10)
        self._path_entry.bind("<Return>", lambda e: self._start())

        # Buttons
        self._browse_btn = self._mk_btn(picker, "📂  Browse", self._browse,
                                         bg=C["panel"], fg=C["text"],
                                         hover_fg=C["accent"])
        self._browse_btn.pack(side="left", padx=(0, 6))

        self._run_btn = self._mk_btn(picker, "▶  Analyze", self._start,
                                      bg=C["accent"], fg=C["bg"],
                                      hover_bg="#79b8ff")
        self._run_btn.pack(side="left")

        # Progress + status
        self._progress = ttk.Progressbar(main, style="D.Horizontal.TProgressbar",
                                          mode="indeterminate")
        status_bar = tk.Frame(main, bg=C["surface"], pady=6)
        status_bar.pack(fill="x")
        tk.Frame(status_bar, bg=C["border"], height=1).pack(fill="x", side="bottom")
        self._status_var = tk.StringVar(value="Select a folder and click Analyze")
        tk.Label(status_bar, textvariable=self._status_var,
                 bg=C["surface"], fg=C["muted"],
                 font=FONT_MONO_SM, padx=20).pack(side="left")

        # ── Content panels ────────────────────────────────────────────────────
        self._content = tk.Frame(main, bg=C["bg"])
        self._content.pack(fill="both", expand=True)

        self._panels = {}
        self._panels["summary"]    = self._build_summary_panel()
        self._panels["complexity"] = self._build_tree_panel(
            cols=("file","loc","funcs","classes","conds","loops","nesting","score","grade"),
            headings=("File","LOC","Fns","Classes","Conds","Loops","Nesting","Score","Grade"),
            widths=(260,50,50,65,60,55,70,70,150),
        )
        self._panels["security"]   = self._build_security_panel()
        self._panels["deps"]       = self._build_tree_panel(
            cols=("source","dep"),
            headings=("Source File","Imports / Depends On"),
            widths=(320, 500),
        )
        self._panels["calls"]      = self._build_tree_panel(
            cols=("caller","callee"),
            headings=("Caller","Calls"),
            widths=(420, 440),
        )

        self._active_panel = None
        self._show_panel("summary")

    # ── Panel builders ────────────────────────────────────────────────────────
    def _build_summary_panel(self) -> tk.Frame:
        f = tk.Frame(self._content, bg=C["bg"])

        lbl = tk.Label(f, text="Summary", bg=C["bg"], fg=C["text"],
                        font=FONT_UI_LG, anchor="w")
        lbl.pack(anchor="w", padx=24, pady=(20, 4))
        tk.Label(f, text="Overview of all analyzed Python files",
                 bg=C["bg"], fg=C["muted"], font=FONT_MONO_SM, anchor="w"
                 ).pack(anchor="w", padx=24, pady=(0, 16))

        # Files tree
        tree, _ = self._make_tree(f,
            cols=("file","funcs","classes","score","grade","issues"),
            headings=("File","Functions","Classes","Score","Grade","Issues"),
            widths=(320,90,80,80,150,80),
        )
        self._summary_tree = tree
        return f

    def _build_security_panel(self) -> tk.Frame:
        f = tk.Frame(self._content, bg=C["bg"])

        tk.Label(f, text="Security Scan", bg=C["bg"], fg=C["text"],
                  font=FONT_UI_LG, anchor="w").pack(anchor="w", padx=24, pady=(20, 4))
        tk.Label(f, text="Detected risky patterns and hardcoded secrets",
                 bg=C["bg"], fg=C["muted"], font=FONT_MONO_SM, anchor="w"
                 ).pack(anchor="w", padx=24, pady=(0, 12))

        # Severity counters
        self._sev_frame = tk.Frame(f, bg=C["bg"])
        self._sev_frame.pack(fill="x", padx=24, pady=(0, 16))
        self._sev_vars = {}
        for sev, color in [("HIGH", C["red"]), ("MEDIUM", C["yellow"]), ("LOW", C["accent"])]:
            card = tk.Frame(self._sev_frame, bg=C["surface"],
                            highlightbackground=color, highlightthickness=1)
            card.pack(side="left", padx=(0, 12), ipadx=20, ipady=12)
            v = tk.StringVar(value="0")
            self._sev_vars[sev] = v
            tk.Label(card, textvariable=v, bg=C["surface"], fg=color,
                     font=("Segoe UI", 26, "bold") if platform.system()=="Windows"
                     else FONT_UI_XL).pack()
            tk.Label(card, text=sev, bg=C["surface"], fg=color,
                     font=FONT_MONO_SM).pack()

        tree, _ = self._make_tree(f,
            cols=("sev","cat","file","line","msg"),
            headings=("Severity","Category","File","Line","Description"),
            widths=(90,130,240,55,360),
        )
        self._sec_tree = tree
        return f

    def _build_tree_panel(self, cols, headings, widths) -> tk.Frame:
        f = tk.Frame(self._content, bg=C["bg"])
        tree, _ = self._make_tree(f, cols=cols, headings=headings, widths=widths)
        return f, tree

    def _make_tree(self, parent, cols, headings, widths):
        wrap = tk.Frame(parent, bg=C["bg"])
        wrap.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Border frame
        border = tk.Frame(wrap, bg=C["border"], padx=1, pady=1)
        border.pack(fill="both", expand=True)

        inner = tk.Frame(border, bg=C["surface"])
        inner.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(inner, orient="vertical", style="D.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(inner, orient="horizontal", style="D.Vertical.TScrollbar")

        tree = ttk.Treeview(inner, columns=cols, show="headings",
                             style="D.Treeview",
                             yscrollcommand=vsb.set,
                             xscrollcommand=hsb.set)

        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)

        for col, heading, width in zip(cols, headings, widths):
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=40, anchor="w", stretch=False)

        # Alternating row tags
        tree.tag_configure("odd",  background=C["surface"])
        tree.tag_configure("even", background=C["panel"])
        tree.tag_configure("high",   foreground=C["red"])
        tree.tag_configure("medium", foreground=C["yellow"])
        tree.tag_configure("low",    foreground=C["accent"])
        tree.tag_configure("grade_a", foreground=C["green"])
        tree.tag_configure("grade_b", foreground="#22d3ee")
        tree.tag_configure("grade_c", foreground=C["yellow"])
        tree.tag_configure("grade_d", foreground=C["orange"])
        tree.tag_configure("grade_f", foreground=C["red"])

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)

        return tree, wrap

    # ── Navigation ────────────────────────────────────────────────────────────
    def _show_panel(self, key: str):
        # Update nav buttons
        for k, btn in self._nav_btns.items():
            if k == key:
                btn.configure(bg=C["panel"], fg=C["accent"],
                               font=FONT_UI_B)
            else:
                btn.configure(bg=C["surface"], fg=C["muted"],
                               font=FONT_UI)

        # Swap panels
        if self._active_panel:
            panel = self._panels[self._active_panel]
            if isinstance(panel, tuple): panel = panel[0]
            panel.pack_forget()

        panel = self._panels[key]
        if isinstance(panel, tuple): panel = panel[0]
        panel.pack(fill="both", expand=True)
        self._active_panel = key

    # ── Button factory ────────────────────────────────────────────────────────
    def _mk_btn(self, parent, text, cmd, bg, fg,
                hover_bg=None, hover_fg=None) -> tk.Button:
        btn = tk.Button(
            parent, text=text, command=cmd,
            bg=bg, fg=fg, activebackground=hover_bg or bg,
            activeforeground=hover_fg or fg,
            relief="flat", font=FONT_UI_B,
            padx=14, pady=7, cursor="hand2", bd=0,
        )
        if hover_bg:
            btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
            btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
        if hover_fg:
            btn.bind("<Enter>", lambda e: btn.configure(fg=hover_fg))
            btn.bind("<Leave>", lambda e: btn.configure(fg=fg))
        return btn

    # ── Actions ───────────────────────────────────────────────────────────────
    def _browse(self):
        path = filedialog.askdirectory(title="Select Python Project Folder")
        if path:
            self._path_var.set(path)
            self._path_entry.xview_moveto(1)

    def _start(self, _event=None):
        path = self._path_var.get().strip()
        if not path:
            self._status_var.set("⚠  Please enter or select a folder path")
            return
        if not os.path.isdir(path):
            self._status_var.set(f"⚠  Not a directory: {path}")
            return

        self._run_btn.configure(state="disabled")
        self._browse_btn.configure(state="disabled")
        self._status_var.set("⏳  Scanning and analyzing…")
        self._progress.pack(fill="x", padx=20)
        self._progress.start(10)
        self._clear_all()

        threading.Thread(target=self._run, args=(path,), daemon=True).start()

    def _run(self, path: str):
        try:
            analyzer = DevLensAnalyzer(path)
            report = analyzer.analyze()
            self.after(0, self._populate, report)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _on_error(self, msg: str):
        self._progress.stop()
        self._progress.pack_forget()
        self._status_var.set(f"✗  {msg}")
        self._run_btn.configure(state="normal")
        self._browse_btn.configure(state="normal")

    # ── Populate ──────────────────────────────────────────────────────────────
    def _populate(self, report):
        self._progress.stop()
        self._progress.pack_forget()
        self._report = report

        n = report.total_files
        self._status_var.set(f"✔  Done — {n} file{'s' if n != 1 else ''} analyzed")

        # Sidebar stats
        self._stat_vars["files"].set(str(report.total_files))
        self._stat_vars["funcs"].set(str(report.total_functions))
        self._stat_vars["classes"].set(str(report.total_classes))
        self._stat_vars["cx"].set(str(report.avg_complexity))
        v = str(report.total_security_issues)
        self._stat_vars["issues"].set(v)

        self._fill_summary(report)
        self._fill_complexity(report)
        self._fill_security(report)
        self._fill_deps(report)
        self._fill_calls(report)

        self._run_btn.configure(state="normal")
        self._browse_btn.configure(state="normal")
        self._show_panel("summary")

    def _fill_summary(self, report):
        tree = self._summary_tree
        tree.delete(*tree.get_children())
        for i, fr in enumerate(sorted(report.files, key=lambda f: f.relative_path)):
            tag = "even" if i % 2 == 0 else "odd"
            if fr.parse_error:
                tree.insert("", "end",
                    values=(fr.relative_path,"—","—","—","PARSE ERROR","—"),
                    tags=(tag,))
                continue
            grade = fr.complexity.get("grade", "—")
            gtag = self._grade_tag(grade)
            tree.insert("", "end",
                values=(
                    fr.relative_path,
                    len(fr.functions),
                    len(fr.classes),
                    fr.complexity.get("score", 0),
                    grade,
                    len(fr.security_issues),
                ),
                tags=(tag, gtag))

    def _fill_complexity(self, report):
        _, tree = self._panels["complexity"]
        tree.delete(*tree.get_children())
        files = sorted(
            [f for f in report.files if not f.parse_error],
            key=lambda f: f.complexity.get("score", 0), reverse=True
        )
        for i, fr in enumerate(files):
            c = fr.complexity
            grade = c.get("grade", "—")
            tag = "even" if i % 2 == 0 else "odd"
            tree.insert("", "end", values=(
                fr.relative_path,
                c.get("lines_of_code", 0),
                c.get("num_functions", 0),
                c.get("num_classes", 0),
                c.get("num_conditionals", 0),
                c.get("num_loops", 0),
                c.get("max_nesting", 0),
                c.get("score", 0),
                grade,
            ), tags=(tag, self._grade_tag(grade)))

    def _fill_security(self, report):
        tree = self._sec_tree
        tree.delete(*tree.get_children())
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        all_issues = []
        for fr in report.files:
            all_issues.extend(fr.security_issues)

        for sev in counts:
            counts[sev] = sum(1 for i in all_issues if i["severity"] == sev)
            self._sev_vars[sev].set(str(counts[sev]))

        order = ["HIGH", "MEDIUM", "LOW"]
        all_issues.sort(key=lambda i: order.index(i["severity"]))
        for i, issue in enumerate(all_issues):
            sev = issue["severity"].lower()
            tag = "even" if i % 2 == 0 else "odd"
            tree.insert("", "end", values=(
                issue["severity"],
                issue["category"],
                issue["file"],
                issue["line"],
                issue["message"],
            ), tags=(tag, sev))

    def _fill_deps(self, report):
        _, tree = self._panels["deps"]
        tree.delete(*tree.get_children())
        i = 0
        for source, deps in sorted(report.dependency_graph.items()):
            for dep in deps:
                tag = "even" if i % 2 == 0 else "odd"
                tree.insert("", "end", values=(source, dep), tags=(tag,))
                i += 1

    def _fill_calls(self, report):
        _, tree = self._panels["calls"]
        tree.delete(*tree.get_children())
        i = 0
        for caller, callees in sorted(report.global_call_graph.items()):
            for callee in callees:
                tag = "even" if i % 2 == 0 else "odd"
                tree.insert("", "end", values=(caller, callee), tags=(tag,))
                i += 1

    def _clear_all(self):
        for v in self._stat_vars.values():
            v.set("…")
        for sev in self._sev_vars:
            self._sev_vars[sev].set("0")
        for key in ["summary", "security"]:
            panel = self._panels[key]
            if isinstance(panel, tuple): panel = panel[0]
        self._summary_tree.delete(*self._summary_tree.get_children())
        self._sec_tree.delete(*self._sec_tree.get_children())
        for key in ["complexity", "deps", "calls"]:
            _, tree = self._panels[key]
            tree.delete(*tree.get_children())

    @staticmethod
    def _grade_tag(grade: str) -> str:
        if not grade: return ""
        g = grade[0]
        return {"A": "grade_a", "B": "grade_b", "C": "grade_c",
                "D": "grade_d", "F": "grade_f"}.get(g, "")


def main():
    app = DevLensApp()
    app.mainloop()


if __name__ == "__main__":
    main()
