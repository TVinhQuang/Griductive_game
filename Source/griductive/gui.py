from __future__ import annotations

from pathlib import Path
from time import monotonic
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from .agent import LogicAgent
from .clues import all_references, describe
from .engine import GameEngine
from .models import Status, SubmissionResult, Verdict
from .puzzles import generate_random_case


class GriductiveApp:
    """A warm, card-first desktop interface around the strictly public SAT agent."""

    PAPER = "#f4ebdd"
    PAPER_2 = "#fffaf2"
    INK = "#2b231f"
    MUTED = "#776c63"
    LINE = "#372d28"
    CORAL = "#f18478"
    CORAL_DARK = "#b94c46"
    SAGE = "#dcebd9"
    GREEN = "#287a4b"
    RED = "#c83934"
    GOLD = "#d99a16"
    BLUE = "#3a8fc2"
    PURPLE = "#8d45b5"
    SHADOW = "#493a32"
    MARKS = (None, "#f6c6c1", "#cde8d1", "#cce4f2", "#e6d4ee", "#f2dfad")

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Griductive — The No-Guess Mystery")
        self.root.geometry("1480x920")
        self.root.minsize(1180, 760)
        self.root.configure(bg=self.PAPER)

        self.agent = LogicAgent()
        self.engine = GameEngine(generate_random_case())
        self.selected: str | None = None
        self.spotlight_owner: str | None = None
        self.highlighted: set[str] = set()
        self.marks: dict[str, int] = {}
        self.card_widgets: dict[str, tk.Frame] = {}
        self.portraits: list[tk.PhotoImage] = []
        self.medium_portraits: list[tk.PhotoImage] = []
        self.small_portraits: list[tk.PhotoImage] = []
        self.tiny_portraits: list[tk.PhotoImage] = []
        self._resize_job: str | None = None
        self._last_board_size = (0, 0)
        self.started_at = monotonic()
        self.paused_seconds = 0.0
        self.hint_target: str | None = None
        self.hint_stage = 0
        self.auto_running = False

        self._load_portraits()
        self._configure_style()
        self._build_shell()
        self.refresh("Case opened. Every visible statement is true — prove before you call.")
        self._tick_timer()
        self.root.after(250, self.show_tutorial)

    def run(self) -> None:
        self.root.mainloop()

    # ---------- setup ----------

    def _load_portraits(self) -> None:
        path = Path(__file__).resolve().parents[1] / "assets" / "suspect_portraits.png"
        try:
            sheet = tk.PhotoImage(file=str(path))
            tile_w, tile_h = sheet.width() // 5, sheet.height() // 5
            for index in range(25):
                col, row = index % 5, index // 5
                tile = tk.PhotoImage(width=tile_w, height=tile_h)
                tile.tk.call(tile, "copy", sheet, "-from", col * tile_w, row * tile_h,
                             (col + 1) * tile_w, (row + 1) * tile_h, "-to", 0, 0)
                self.portraits.append(tile.subsample(3, 3))
                self.medium_portraits.append(tile.subsample(4, 4))
                self.small_portraits.append(tile.subsample(6, 6))
                self.tiny_portraits.append(tile.subsample(8, 8))
        except tk.TclError:
            # The game remains playable if the optional art asset cannot be decoded.
            self.portraits = [tk.PhotoImage(width=1, height=1) for _ in range(25)]
            self.medium_portraits = self.portraits[:]
            self.small_portraits = self.portraits[:]
            self.tiny_portraits = self.portraits[:]

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Paper.TFrame", background=self.PAPER)
        style.configure("Card.TFrame", background=self.PAPER_2)
        style.configure("Paper.TLabel", background=self.PAPER, foreground=self.INK, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=self.PAPER, foreground=self.MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=self.PAPER, foreground=self.INK, font=("Georgia", 30, "bold"))
        style.configure("Section.TLabel", background=self.PAPER, foreground=self.INK, font=("Georgia", 14, "bold"))
        style.configure("Ink.TButton", font=("Segoe UI Semibold", 10), padding=(12, 8), background=self.PAPER_2,
                        foreground=self.INK, bordercolor=self.LINE, relief="solid")
        style.map("Ink.TButton", background=[("active", "#eadfd1")])
        style.configure("Coral.TButton", font=("Segoe UI Semibold", 10), padding=(12, 8), background=self.CORAL,
                        foreground=self.INK, bordercolor=self.LINE, relief="solid")
        style.map("Coral.TButton", background=[("active", "#f59a8f")])
        style.configure("TCombobox", fieldbackground=self.PAPER_2, background=self.PAPER_2, foreground=self.INK,
                        arrowcolor=self.INK, bordercolor=self.LINE)

    def _build_shell(self) -> None:
        self._build_topbar()
        body = tk.Frame(self.root, bg=self.PAPER)
        body.pack(fill="both", expand=True, padx=26, pady=(8, 10))
        body.grid_columnconfigure(0, minsize=280, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, minsize=292, weight=0)
        body.grid_rowconfigure(0, weight=1)

        self.info_panel = tk.Frame(body, bg=self.PAPER, width=280, padx=16, pady=20)
        self.info_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        self.info_panel.pack_propagate(False)
        self.board_panel = tk.Frame(body, bg=self.PAPER)
        self.board_panel.grid(row=0, column=1, sticky="nsew")
        self.board_panel.grid_rowconfigure(1, weight=1)
        self.board_panel.grid_columnconfigure(0, weight=1)
        self.board_panel.bind("<Configure>", self._on_board_resize)
        self.logic_panel = tk.Frame(body, bg=self.PAPER_2, width=292, highlightbackground="#d8cbbd",
                                    highlightthickness=1, padx=16, pady=16)
        self.logic_panel.grid(row=0, column=2, sticky="nsew", padx=(15, 0))
        self.logic_panel.pack_propagate(False)

        self._build_info_panel()
        self._build_logic_panel()
        self._build_bottom_bar()

    def _build_topbar(self) -> None:
        top = tk.Frame(self.root, bg=self.PAPER_2, height=58, highlightbackground="#ded2c5", highlightthickness=1)
        top.pack(fill="x")
        top.pack_propagate(False)
        brand = tk.Label(top, text="♟  GRIDUCTIVE", bg=self.PAPER_2, fg=self.INK, font=("Georgia", 18, "bold"))
        brand.pack(side="left", padx=28)

        center = tk.Frame(top, bg=self.PAPER_2)
        center.pack(side="left", expand=True)
        tk.Label(center, text="RANDOM CASE", bg=self.PAPER_2, fg=self.MUTED,
                 font=("Consolas", 9, "bold")).pack(side="left", padx=(0, 7))
        self.case_code_var = tk.StringVar()
        tk.Label(center, textvariable=self.case_code_var, bg=self.PAPER_2, fg=self.INK,
                 font=("Consolas", 10, "bold"), padx=9).pack(side="left")
        ttk.Button(center, text="✦  New Random Case", command=self.new_random_case,
                   style="Coral.TButton").pack(side="left", padx=6)
        ttk.Button(center, text="↺  Replay Seed", command=self.show_seed_replay,
                   style="Ink.TButton").pack(side="left", padx=2)

        right = tk.Frame(top, bg=self.PAPER_2)
        right.pack(side="right", padx=22)
        self.timer_var = tk.StringVar(value="00:00")
        tk.Label(right, textvariable=self.timer_var, bg=self.PAPER_2, fg=self.INK,
                 font=("Consolas", 13, "bold")).pack(side="left", padx=12)
        ttk.Button(right, text="?  How to play", command=self.show_tutorial, style="Ink.TButton").pack(side="left")

    def _build_info_panel(self) -> None:
        ttk.Label(self.info_panel, text="THE DAILY CASE", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(self.info_panel, text="Griductive", style="Title.TLabel").pack(anchor="w", pady=(5, 2))
        ttk.Label(self.info_panel, text="A grid-deduction mystery.\nNo guesses. Only proof.", style="Paper.TLabel",
                  font=("Segoe UI", 12), justify="left").pack(anchor="w", pady=(0, 16))

        tk.Frame(self.info_panel, bg="#d8cbbd", height=1, width=55).pack(anchor="w", pady=(0, 18))
        ttk.Label(self.info_panel, text="HOW TO PLAY", style="Muted.TLabel").pack(anchor="w")
        rules = (
            "✦  Tap a suspect to open the verdict card.",
            "↻  A proved call flips the card and reveals a clue.",
            "◇  Tap a solved card to spotlight everyone it counts.",
            "✎  Mark cards with pencil-note colors.",
            "☼  Hint has two stages: clue, then verdict.",
        )
        for rule in rules:
            tk.Label(self.info_panel, text=rule, bg=self.PAPER, fg=self.INK, wraplength=245,
                     justify="left", anchor="w", font=("Segoe UI", 10), pady=5).pack(fill="x")

        self.case_badge = tk.Label(self.info_panel, bg="#efe2d5", fg=self.INK, padx=12, pady=9,
                                   font=("Consolas", 9, "bold"), justify="left")
        self.case_badge.pack(fill="x", pady=(22, 8))
        self.progress_canvas = tk.Canvas(self.info_panel, height=22, bg=self.PAPER, highlightthickness=0)
        self.progress_canvas.pack(fill="x")

    def _build_logic_panel(self) -> None:
        tk.Label(self.logic_panel, text="PUBLIC KNOWLEDGE", bg=self.PAPER_2, fg=self.INK,
                 font=("Georgia", 14, "bold")).pack(anchor="w")
        self.progress_var = tk.StringVar()
        tk.Label(self.logic_panel, textvariable=self.progress_var, bg=self.PAPER_2, fg=self.MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 12))

        self.detail_title = tk.StringVar(value="Select a card")
        tk.Label(self.logic_panel, textvariable=self.detail_title, bg=self.PAPER_2, fg=self.INK,
                 font=("Segoe UI Semibold", 12), anchor="w", justify="left", wraplength=250).pack(fill="x")
        self.detail = tk.Text(self.logic_panel, height=9, wrap="word", bg=self.PAPER_2, fg=self.INK, relief="flat",
                              highlightthickness=0, font=("Segoe UI", 10), padx=0, pady=8, state="disabled")
        self.detail.pack(fill="x")
        self.clear_spotlight_button = ttk.Button(self.logic_panel, text="×  Clear spotlight", command=self.clear_spotlight,
                                                 style="Ink.TButton")
        self.clear_spotlight_button.pack(fill="x", pady=(0, 12))

        tk.Frame(self.logic_panel, bg="#ded2c5", height=1).pack(fill="x", pady=4)
        tk.Label(self.logic_panel, text="SOLVER METRICS", bg=self.PAPER_2, fg=self.INK,
                 font=("Segoe UI Semibold", 10)).pack(anchor="w", pady=(9, 3))
        self.metrics_var = tk.StringVar()
        tk.Label(self.logic_panel, textvariable=self.metrics_var, bg=self.PAPER_2, fg=self.MUTED,
                 font=("Consolas", 8), justify="left").pack(anchor="w")

        tk.Label(self.logic_panel, text="DEDUCTION TRACE", bg=self.PAPER_2, fg=self.INK,
                 font=("Segoe UI Semibold", 10)).pack(anchor="w", pady=(13, 4))
        trace_frame = tk.Frame(self.logic_panel, bg=self.PAPER_2)
        trace_frame.pack(fill="both", expand=True)
        self.trace_list = tk.Listbox(trace_frame, bg="#f8f1e7", fg=self.INK, selectbackground="#ead8c7",
                                     selectforeground=self.INK, relief="flat", highlightbackground="#d8cbbd",
                                     highlightthickness=1, font=("Consolas", 8), activestyle="none")
        scrollbar = ttk.Scrollbar(trace_frame, orient="vertical", command=self.trace_list.yview)
        self.trace_list.configure(yscrollcommand=scrollbar.set)
        self.trace_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_bottom_bar(self) -> None:
        bar = tk.Frame(self.root, bg=self.PAPER, pady=9)
        bar.pack(fill="x", side="bottom")
        actions = tk.Frame(bar, bg=self.PAPER)
        actions.pack()
        ttk.Button(actions, text="✎  Mark", command=self.mark_selected, style="Ink.TButton").pack(side="left", padx=5)
        ttk.Button(actions, text="☼  Hint", command=self.hint, style="Ink.TButton").pack(side="left", padx=5)
        ttk.Button(actions, text="▶  Auto Solve", command=self.auto_solve, style="Coral.TButton").pack(side="left", padx=5)
        ttk.Button(actions, text="↻  Restart", command=self.restart, style="Ink.TButton").pack(side="left", padx=5)
        self.status_var = tk.StringVar()
        tk.Label(bar, textvariable=self.status_var, bg=self.PAPER, fg=self.MUTED, font=("Segoe UI", 9),
                 anchor="center").pack(pady=(7, 0))

    # ---------- board ----------

    def _draw_board(self) -> None:
        for child in self.board_panel.winfo_children():
            child.destroy()
        self.card_widgets.clear()
        puzzle = self.engine.puzzle
        public = self.engine.public_state()
        labels = {character.cell: character.name for character in puzzle.characters}
        layout = self._responsive_card_layout(puzzle.rows, puzzle.columns)

        heading = tk.Frame(self.board_panel, bg=self.PAPER)
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        tk.Label(heading, text=puzzle.title, bg=self.PAPER, fg=self.INK,
                 font=("Georgia", layout["heading_font"], "bold")).pack(side="left")
        if layout["card_width"] >= 105:
            tk.Label(heading, text="Tap a revealed clue to inspect its reach", bg=self.PAPER, fg=self.MUTED,
                     font=("Segoe UI", 8)).pack(side="right")

        grid = tk.Frame(self.board_panel, bg=self.PAPER)
        grid.grid(row=1, column=0, sticky="nsew")
        for index in range(puzzle.columns):
            grid.grid_columnconfigure(index, weight=1, uniform="cards")
        for index in range(puzzle.rows):
            grid.grid_rowconfigure(index, weight=1, uniform="cards")

        characters = {character.cell: character for character in puzzle.characters}
        for row in range(puzzle.rows):
            for col in range(puzzle.columns):
                cell = f"{chr(65 + col)}{row + 1}"
                character = characters[cell]
                known = cell in public.known_verdicts
                marked = self.MARKS[self.marks.get(cell, 0)]
                bg = self.PAPER_2 if marked is None else marked
                border = self.LINE
                thickness = 2
                if self.spotlight_owner:
                    if cell == self.spotlight_owner:
                        border, thickness = self.GOLD, 5
                    elif cell in self.highlighted:
                        border, thickness = self.BLUE, 5
                    else:
                        bg = "#e6ddd2"
                        border = "#a79c91"
                elif cell == self.selected:
                    border, thickness = self.PURPLE, 5
                elif known:
                    border = self.GREEN if public.known_verdicts[cell] is Status.INNOCENT else self.RED

                card = tk.Frame(grid, bg=bg, highlightbackground=border, highlightcolor=border,
                                highlightthickness=thickness, cursor="hand2")
                card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
                self.card_widgets[cell] = card
                self._populate_card(card, cell, character, known, public, labels, layout)
                self._bind_tree(card, lambda _event, c=cell: self.select(c))

    def _populate_card(self, card: tk.Frame, cell, character, known, public, labels, layout) -> None:
        bg = card.cget("bg")
        top = tk.Frame(card, bg=bg)
        top.pack(fill="x", padx=layout["inner_pad"], pady=(layout["top_pad"], 0))
        tk.Label(top, text=cell, bg=bg, fg=self.MUTED,
                 font=("Consolas", layout["coord_font"], "bold")).pack(side="left")
        if self.marks.get(cell, 0):
            tk.Label(top, text="✎", bg=bg, fg=self.INK,
                     font=("Segoe UI", layout["coord_font"] + 1)).pack(side="right")
        index = character.portrait_index
        if known:
            header = tk.Frame(card, bg=bg)
            header.pack(fill="x", padx=layout["inner_pad"], pady=(0, 0))
            known_portrait = self.tiny_portraits[index] if layout["compact"] else self.small_portraits[index]
            tk.Label(header, image=known_portrait, bg=bg).pack(side="left")
            identity = tk.Frame(header, bg=bg)
            identity.pack(side="left", padx=max(1, layout["inner_pad"] - 2))
            tk.Label(identity, text=character.name, bg=bg, fg=self.INK,
                     font=("Segoe UI Semibold", layout["known_name_font"])).pack(anchor="w")
            status = public.known_verdicts[cell]
            tk.Label(identity, text=status.value, bg=bg, fg=self.GREEN if status is Status.INNOCENT else self.RED,
                     font=("Consolas", layout["status_font"], "bold")).pack(anchor="w")
            clue = describe(self.engine.puzzle.clues[cell], labels)
            portrait_height = 31 if layout["compact"] else 41
            clue_height = max(28, layout["card_height"] - portrait_height - layout["header_reserve"])
            clue_font = self._fit_text_size(
                clue, layout["text_width"], clue_height,
                maximum=layout["clue_max_font"], minimum=5,
            )
            tk.Label(card, text=clue, bg=bg, fg=self.INK, wraplength=layout["text_width"],
                     justify="center", anchor="center", font=("Segoe UI", clue_font)).pack(
                         fill="both", expand=True, padx=layout["inner_pad"], pady=(0, layout["bottom_pad"])
                     )
        else:
            portrait_set = self.portraits
            if layout["compact"]:
                portrait_set = self.medium_portraits if layout["card_width"] >= 82 else self.small_portraits
            tk.Label(card, image=portrait_set[index], bg=bg).pack(expand=True, pady=(0, 0))
            tk.Label(card, text=character.name, bg=bg, fg=self.INK,
                     font=("Segoe UI Semibold", layout["name_font"])).pack()
            tk.Label(card, text=character.profession.upper(), bg=bg, fg=self.MUTED,
                     wraplength=layout["text_width"], justify="center",
                     font=("Consolas", layout["profession_font"], "bold")).pack(
                         pady=(0, layout["bottom_pad"])
                     )

    def _responsive_card_layout(self, rows: int, columns: int) -> dict[str, int | bool]:
        """Derive card typography and art size from the actual board viewport."""
        panel_width = self.board_panel.winfo_width()
        panel_height = self.board_panel.winfo_height()
        if panel_width <= 1:
            panel_width = 650
        if panel_height <= 1:
            panel_height = 700
        self._last_board_size = (panel_width, panel_height)
        card_width = max(55, int((panel_width - 8 * columns) / columns))
        card_height = max(72, int((panel_height - 42 - 8 * rows) / rows))
        compact = card_width < 118 or card_height < 155
        scale = min(card_width / 130, card_height / 170, 1.0)
        return {
            "card_width": card_width,
            "card_height": card_height,
            "compact": compact,
            "heading_font": 13 if panel_width < 520 else 16,
            "coord_font": max(6, round(8 * scale)),
            "name_font": max(8, round(11 * scale)),
            "profession_font": max(5, round(7 * scale)),
            "known_name_font": max(7, round(9 * scale)),
            "status_font": max(5, round(7 * scale)),
            "clue_max_font": max(6, round(9 * scale)),
            "inner_pad": 2 if compact else 5,
            "top_pad": 2 if compact else 4,
            "bottom_pad": 2 if compact else 5,
            "text_width": max(42, card_width - (8 if compact else 14)),
            "header_reserve": 49 if compact else 62,
        }

    def _fit_text_size(self, text: str, width: int, height: int,
                       maximum: int = 9, minimum: int = 5) -> int:
        """Return the largest font whose measured wrapped lines fit the available card area."""
        for size in range(maximum, minimum - 1, -1):
            font = tkfont.Font(root=self.root, family="Segoe UI", size=size)
            lines = 1
            current = ""
            for word in text.split():
                candidate = word if not current else f"{current} {word}"
                if font.measure(candidate) <= width:
                    current = candidate
                else:
                    if current:
                        lines += 1
                    # Tk can character-wrap a single word; account for that space as extra lines.
                    word_width = font.measure(word)
                    if word_width > width:
                        lines += max(0, (word_width - 1) // max(width, 1))
                    current = word
            if lines * font.metrics("linespace") <= height:
                return size
        return minimum

    def _on_board_resize(self, event: tk.Event) -> None:
        """Debounce redraws while the user drags the window edge."""
        if event.width < 100 or event.height < 100:
            return
        previous_width, previous_height = self._last_board_size
        if abs(event.width - previous_width) < 5 and abs(event.height - previous_height) < 5:
            return
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(120, self._finish_responsive_resize)

    def _finish_responsive_resize(self) -> None:
        self._resize_job = None
        self._draw_board()

    @staticmethod
    def _bind_tree(widget: tk.Widget, callback) -> None:
        widget.bind("<Button-1>", callback)
        for child in widget.winfo_children():
            GriductiveApp._bind_tree(child, callback)

    # ---------- game actions ----------

    def new_random_case(self) -> None:
        self.engine = GameEngine(generate_random_case())
        self._reset_view_state()
        self.refresh(f"Generated a new {self.engine.puzzle.rows}×{self.engine.puzzle.columns} case. "
                     "The roster, positions, statuses and clue chain are all new.")

    def show_seed_replay(self) -> None:
        modal, box = self._modal("Replay a case seed", 430, 290)
        tk.Label(box, text="Enter the eight-digit hexadecimal seed shown in a case header. The exact board, roster and clues will be rebuilt.",
                 bg=self.PAPER_2, fg=self.MUTED, wraplength=340, justify="left",
                 font=("Segoe UI", 10)).pack(padx=12, pady=(4, 12))
        seed_var = tk.StringVar(value=f"{self.engine.puzzle.seed:08X}")
        entry = tk.Entry(box, textvariable=seed_var, bg="#f8f1e7", fg=self.INK, relief="solid", bd=1,
                         justify="center", font=("Consolas", 15, "bold"))
        entry.pack(fill="x", padx=24, pady=6)
        error_var = tk.StringVar()
        tk.Label(box, textvariable=error_var, bg=self.PAPER_2, fg=self.RED,
                 font=("Segoe UI", 9)).pack()

        def replay() -> None:
            try:
                raw = seed_var.get().strip().removeprefix("#")
                seed = int(raw, 16)
                if not 0 < seed < 2**31:
                    raise ValueError
                self.engine = GameEngine(generate_random_case(seed))
            except ValueError:
                error_var.set("Use a valid seed from 00000001 to 7FFFFFFF.")
                return
            modal.destroy()
            self._reset_view_state()
            self.refresh(f"Replayed case seed #{seed:08X} exactly.")

        self._modal_button(box, "Replay this case", self.CORAL, self.INK, replay).pack(fill="x", padx=24, pady=(8, 0))
        entry.focus_set()
        entry.select_range(0, "end")
        modal.bind("<Return>", lambda _event: replay())

    def restart(self) -> None:
        self.engine.restart()
        self._reset_view_state()
        self.refresh("Case restarted. Pencil marks, timer and spotlight were cleared.")

    def _reset_view_state(self) -> None:
        self.selected = self.spotlight_owner = None
        self.highlighted.clear()
        self.marks.clear()
        self.hint_target = None
        self.hint_stage = 0
        self.started_at = monotonic()
        self.auto_running = False

    def select(self, cell: str) -> None:
        if self.auto_running:
            return
        public = self.engine.public_state()
        self.selected = cell
        if cell in public.known_verdicts:
            clue = self.engine.puzzle.clues[cell]
            self.spotlight_owner = cell
            self.highlighted = set(all_references(clue))
            self.detail_title.set(f"{clue.id} · {self._name(cell)}'s statement")
            self._set_detail(describe(clue, {c.cell: c.name for c in public.characters}) +
                             "\n\nGold is the clue owner. Blue cards are the people or cells this statement counts.")
            self.refresh("Clue spotlight active. The rest of the board is dimmed.")
        else:
            self.clear_spotlight(redraw=False)
            self._show_verdict_modal(cell)

    def _show_verdict_modal(self, cell: str) -> None:
        character = next(item for item in self.engine.puzzle.characters if item.cell == cell)
        index = character.portrait_index
        modal, box = self._modal("Innocent or criminal?", 430, 480)
        tk.Label(box, image=self.portraits[index], bg=self.PAPER_2).pack(pady=(4, 0))
        tk.Label(box, text=character.name, bg=self.PAPER_2, fg=self.INK, font=("Georgia", 18, "bold")).pack()
        tk.Label(box, text=f"{cell}  ·  {character.profession}", bg=self.PAPER_2, fg=self.MUTED,
                 font=("Consolas", 9)).pack(pady=(0, 17))
        tk.Label(box, text="Only lock a verdict the revealed statements actually prove.\nA correct call flips the card and reveals the next lead.",
                 bg=self.PAPER_2, fg=self.MUTED, justify="center", font=("Segoe UI", 10), wraplength=340).pack(pady=(0, 15))
        actions = tk.Frame(box, bg=self.PAPER_2)
        actions.pack(fill="x", padx=18)
        self._modal_button(actions, "INNOCENT", self.SAGE, self.GREEN,
                           lambda: self._submit_from_modal(modal, cell, Status.INNOCENT)).pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._modal_button(actions, "CRIMINAL", "#f7cbc7", self.RED,
                           lambda: self._submit_from_modal(modal, cell, Status.CRIMINAL)).pack(side="left", fill="x", expand=True, padx=(5, 0))
        self._modal_button(box, "Cancel", self.PAPER_2, self.MUTED, modal.destroy).pack(fill="x", padx=18, pady=(10, 0))

    def _submit_from_modal(self, modal: tk.Toplevel, cell: str, proposed: Status) -> None:
        modal.destroy()
        result = self.engine.submit(cell, proposed, self.agent)
        if result is SubmissionResult.ACCEPTED:
            self.selected = cell
            self.spotlight_owner = None
            self.highlighted.clear()
            self.refresh(f"Correct call — {self._name(cell)} is {proposed.value.lower()}. A new statement has been revealed.")
            self._animate_flip(cell, 0)
            if self.engine.is_solved():
                self.root.after(450, self._show_completion)
            return
        if result in (SubmissionResult.NOT_PROVABLE, SubmissionResult.CONTRADICTED):
            self._show_feedback(cell, proposed, result)
        else:
            self.refresh(result.value)

    def _show_feedback(self, cell: str, proposed: Status, result: SubmissionResult) -> None:
        title = "Conclusion not possible" if result is SubmissionResult.NOT_PROVABLE else "Verdict contradicted"
        modal, box = self._modal(title, 440, 340)
        tk.Label(box, text="△", bg=self.PAPER_2, fg=self.GOLD if result is SubmissionResult.NOT_PROVABLE else self.RED,
                 font=("Segoe UI", 36)).pack()
        if result is SubmissionResult.NOT_PROVABLE:
            text = (f"You cannot yet prove that {self._name(cell)} is {proposed.value.lower()}.\n\n"
                    "There is still a consistent case for both possibilities. Unlock more testimony or lean on a hint.")
        else:
            text = (f"The current public knowledge forces the opposite of {proposed.value.lower()} for {self._name(cell)}.\n\n"
                    "No hidden clue was revealed and the case state is unchanged.")
        tk.Label(box, text=text, bg=self.PAPER_2, fg=self.MUTED, wraplength=350, justify="center",
                 font=("Segoe UI", 10)).pack(padx=20, pady=(0, 18))
        self._modal_button(box, "Keep investigating", self.CORAL, self.INK, modal.destroy).pack(fill="x", padx=24)
        self.refresh(f"{result.value}: the card stayed face down.")

    def mark_selected(self) -> None:
        if self.selected is None:
            self.refresh("Select a card before adding a pencil mark.")
            return
        if self.selected in self.engine.public_state().known_verdicts:
            self.refresh("Solved cards already have a proved status; pencil marks are for open suspects.")
            return
        self.marks[self.selected] = (self.marks.get(self.selected, 0) + 1) % len(self.MARKS)
        label = "cleared" if self.marks[self.selected] == 0 else f"color {self.marks[self.selected]}"
        self.refresh(f"Pencil mark on {self.selected}: {label}. Marks never enter the logic agent's KB.")

    def hint(self) -> None:
        item = self.agent.next_forced(self.engine.public_state())
        if item is None or item.verdict is Verdict.INCONSISTENT:
            self.refresh("No safe hint is available from the current public knowledge.")
            return
        if self.hint_target != item.cell:
            self.hint_target, self.hint_stage = item.cell, 0
        related = next((clue.owner for clue in self.engine.public_state().revealed_clues
                        if item.cell in all_references(clue)), None)
        if self.hint_stage == 0 and related:
            self.hint_stage = 1
            self.select(related)
            self.status_var.set(f"Hint 1/2: inspect {self.engine.puzzle.clues[related].id}; it concerns {item.cell}.")
        else:
            self.hint_stage = 0
            self.selected = item.cell
            self.clear_spotlight(redraw=False)
            self.refresh(f"Hint 2/2: {item.cell} can be proved {item.verdict.value}. No hidden solution was consulted.")

    def auto_solve(self) -> None:
        if self.auto_running:
            return
        self.auto_running = True
        self.clear_spotlight(redraw=False)
        self.status_var.set("Auto Solve is deriving one public verdict at a time…")
        self._auto_step()

    def _auto_step(self) -> None:
        if self.engine.is_solved():
            self.auto_running = False
            self.refresh("Auto Solve completed the case without guessing.")
            self._show_completion()
            return
        result, item = self.engine.auto_step(self.agent)
        if result is not SubmissionResult.ACCEPTED or item is None:
            self.auto_running = False
            self.refresh(f"Auto Solve stopped: {result.value}.")
            return
        self.selected = item.cell
        self.refresh(f"Derived {item.cell} = {item.verdict.value}; revealing the next statement…")
        self._animate_flip(item.cell, 0)
        self.root.after(420, self._auto_step)

    def clear_spotlight(self, redraw: bool = True) -> None:
        self.spotlight_owner = None
        self.highlighted.clear()
        if redraw:
            self.refresh("Spotlight cleared.")

    # ---------- feedback and tutorial ----------

    def _animate_flip(self, cell: str, step: int) -> None:
        card = self.card_widgets.get(cell)
        if card is None or step >= 6:
            self.refresh(None)
            return
        colors = (self.PAPER_2, self.CORAL, self.PAPER_2, self.SAGE, self.PAPER_2, self.SAGE)
        card.configure(bg=colors[step], highlightbackground=self.GOLD, highlightthickness=5)
        self.root.after(55, lambda: self._animate_flip(cell, step + 1))

    def _show_completion(self) -> None:
        modal, box = self._modal("Case solved", 470, 390)
        tk.Label(box, text="✦", bg=self.PAPER_2, fg=self.GOLD, font=("Georgia", 42, "bold")).pack()
        tk.Label(box, text="Every suspect identified", bg=self.PAPER_2, fg=self.INK,
                 font=("Georgia", 20, "bold")).pack()
        elapsed = self.timer_var.get()
        tk.Label(box, text=f"Solved in {elapsed} with {len(self.engine.trace)} derived reveal steps.\nEvery call followed from public knowledge — zero guesses.",
                 bg=self.PAPER_2, fg=self.MUTED, justify="center", font=("Segoe UI", 10), wraplength=370).pack(pady=16)
        self._modal_button(box, "Play another case", self.CORAL, self.INK,
                           lambda: (modal.destroy(), self._next_case())).pack(fill="x", padx=24, pady=4)
        self._modal_button(box, "Review deduction trace", self.PAPER_2, self.MUTED, modal.destroy).pack(fill="x", padx=24, pady=4)

    def _next_case(self) -> None:
        self.new_random_case()

    def show_tutorial(self) -> None:
        modal, box = self._modal("How to play", 720, 650)
        canvas = tk.Canvas(box, bg=self.PAPER_2, highlightthickness=0)
        scroll = ttk.Scrollbar(box, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=self.PAPER_2)
        content.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw", width=620)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(4, 0))
        scroll.pack(side="right", fill="y")

        sections = (
            ("THE LOOP", "Prove, call, reveal",
             "Every person is secretly criminal or innocent. Tap an open suspect and submit only a verdict forced by the revealed statements. A correct call flips the card and reveals that person's always-true clue."),
            ("NO GUESSING", "What rejection means",
             "NOT_PROVABLE means both outcomes still fit the public facts. CONTRADICTED means the opposite outcome is forced. A rejected call never reveals hidden information and never changes the case."),
            ("CLUE SPOTLIGHT", "See exactly who a statement counts",
             "Tap any solved card. Its owner receives a gold border, referenced cards receive blue borders, and unrelated cards dim. Use Clear spotlight when you are done."),
            ("PENCIL NOTES", "Organize your hunches safely",
             "Select an open card, then press Mark to cycle red, green, blue, purple and gold notes. These marks are purely visual and are never sent to the SAT solver."),
            ("TWO-STAGE HINT", "A nudge before the answer",
             "The first press spotlights a relevant revealed clue. Press Hint again to identify the next provable person and verdict. The hint agent sees public knowledge only."),
            ("RANDOM CASES", "A different board every time",
             "Every launch and every New Random Case chooses rows and columns independently from 3 to 5, then shuffles the roster, positions, hidden verdicts and reveal chains. The case seed in the header makes any board reproducible for testing."),
            ("AUTO SOLVE", "Watch the deduction engine",
             "Auto Solve checks logical entailment with DPLL, reveals one forced card at a time, and records SAT calls, decisions, propagations, backtracks and runtime in the trace panel."),
        )
        intro = tk.Label(content, text="Exactly one complete line-up fits the full case. Read the clues, prove each verdict, and identify everyone — one public deduction at a time.",
                         bg="#f9eee7", fg=self.INK, wraplength=565, justify="left", padx=16, pady=14,
                         font=("Segoe UI", 11))
        intro.pack(fill="x", padx=12, pady=(4, 16))
        for eyebrow, title, text in sections:
            tk.Label(content, text=eyebrow, bg=self.PAPER_2, fg=self.CORAL_DARK,
                     font=("Consolas", 8, "bold")).pack(anchor="w", padx=16)
            tk.Label(content, text=title, bg=self.PAPER_2, fg=self.INK,
                     font=("Georgia", 16, "bold")).pack(anchor="w", padx=16, pady=(2, 3))
            tk.Label(content, text=text, bg=self.PAPER_2, fg=self.MUTED, wraplength=570, justify="left",
                     font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(0, 16))
        self._modal_button(content, "Got it — open the case", self.CORAL, self.INK, modal.destroy).pack(fill="x", padx=16, pady=(4, 14))

    def _modal(self, title: str, width: int, height: int) -> tuple[tk.Toplevel, tk.Frame]:
        modal = tk.Toplevel(self.root)
        modal.title(title)
        modal.configure(bg=self.SHADOW)
        modal.transient(self.root)
        modal.grab_set()
        modal.resizable(False, False)
        x = self.root.winfo_rootx() + max(20, (self.root.winfo_width() - width) // 2)
        y = self.root.winfo_rooty() + max(20, (self.root.winfo_height() - height) // 2)
        modal.geometry(f"{width}x{height}+{x}+{y}")
        shadow = tk.Frame(modal, bg=self.SHADOW)
        shadow.pack(fill="both", expand=True, padx=(0, 8), pady=(0, 8))
        box = tk.Frame(shadow, bg=self.PAPER_2, highlightbackground=self.LINE, highlightthickness=2, padx=22, pady=18)
        box.pack(fill="both", expand=True)
        header = tk.Frame(box, bg=self.PAPER_2)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text=title, bg=self.PAPER_2, fg=self.INK, font=("Georgia", 18, "bold")).pack(side="left")
        tk.Button(header, text="×", command=modal.destroy, bg=self.PAPER_2, fg=self.INK, relief="flat",
                  font=("Segoe UI", 15), cursor="hand2").pack(side="right")
        modal.bind("<Escape>", lambda _event: modal.destroy())
        return modal, box

    def _modal_button(self, parent, text, bg, fg, command) -> tk.Button:
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg,
                         activeforeground=fg, relief="solid", bd=2, cursor="hand2",
                         font=("Segoe UI Semibold", 10), pady=9)

    # ---------- refresh ----------

    def refresh(self, message: str | None) -> None:
        public = self.engine.public_state()
        if message is not None:
            self.status_var.set(message)
        solved, total = len(public.known_verdicts), len(public.characters)
        self.progress_var.set(f"{solved} / {total} verdicts proved  ·  {len(public.revealed_clues)} clues public")
        self.case_code_var.set(
            f"{self.engine.puzzle.rows}×{self.engine.puzzle.columns}  ·  #{self.engine.puzzle.seed:08X}"
        )
        self.case_badge.configure(
            text=f"CASE  {self.engine.puzzle.rows}×{self.engine.puzzle.columns}\n"
                 f"{solved:02d} CLEARED  ·  {total - solved:02d} OPEN\n"
                 f"SEED  {self.engine.puzzle.seed:08X}"
        )
        self._draw_progress(solved, total)

        classification = self.agent.classify_all(public)
        encoded = classification.encoded
        stats = self._trace_stats()
        self.metrics_var.set(
            f"PRIMARY VARS   {encoded.primary_variables}\nAUX VARS       {encoded.auxiliary_variables}\nCNF CLAUSES    {len(encoded.clauses)}\n"
            f"SAT CALLS      {stats[0]}\nDECISIONS      {stats[1]}\nPROPAGATIONS   {stats[2]}\nBACKTRACKS     {stats[3]}\nTIME           {stats[4]:.2f} ms"
        )
        self.trace_list.delete(0, "end")
        for item in self.engine.trace:
            self.trace_list.insert("end", f"{item.step:02}  {item.cell:<3} {item.verdict.value:<9} → {item.revealed_clue_id}")
        if self.engine.trace:
            self.trace_list.see("end")
        self._draw_board()

    def _draw_progress(self, solved: int, total: int) -> None:
        self.progress_canvas.delete("all")
        width = max(200, self.progress_canvas.winfo_width())
        gap = min(16, (width - 15) / max(total, 1))
        start = 7
        for index in range(total):
            color = self.CORAL if index < solved else "#c9beb3"
            self.progress_canvas.create_oval(start + index * gap, 6, start + index * gap + 8, 14, fill=color, outline="")

    def _trace_stats(self) -> tuple[int, int, int, int, float]:
        stats = [entry.stats for entry in self.engine.trace]
        return (sum(s.sat_calls for s in stats), sum(s.decisions for s in stats),
                sum(s.propagations for s in stats), sum(s.backtracks for s in stats),
                sum(s.runtime_ms for s in stats))

    def _tick_timer(self) -> None:
        elapsed = int(monotonic() - self.started_at - self.paused_seconds)
        self.timer_var.set(f"{elapsed // 60:02d}:{elapsed % 60:02d}")
        self.root.after(1000, self._tick_timer)

    def _set_detail(self, value: str) -> None:
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", value)
        self.detail.configure(state="disabled")

    def _name(self, cell: str) -> str:
        return next(item.name for item in self.engine.puzzle.characters if item.cell == cell)
