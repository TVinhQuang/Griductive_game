# Griductive Solver - source guide

Run `python main.py` from this directory. No third-party packages are required.

## Player experience

The redesigned Tkinter interface is inspired by a cozy tabletop mystery rather than a developer dashboard. It includes 25 original illustrated suspect portraits, responsive rectangular card boards from 3x3 through 5x5, an onboarding tutorial, verdict and rejection dialogs, card-reveal feedback, a case timer, visual progress, clue spotlighting, five pencil-note colors, a two-stage public-knowledge Hint, animated Auto Solve, a completion screen, solver metrics, and a scrolling deduction trace. Card typography is measured and fitted against the live viewport: resizing the window automatically changes portrait resolution, padding, wrapping width, and font size so revealed statements remain fully visible.

The portrait sprite sheet lives at `assets/suspect_portraits.png`. Tkinter crops it into 25 in-memory card portraits at startup, so Pillow or another image package is not required.

## Architecture

`griductive.engine.GameEngine` owns the complete `Puzzle`, including private solution labels and unrevealed clues. Its `public_state()` method returns only character metadata, currently revealed clues, and previously proved verdicts.

`griductive.agent.LogicAgent` accepts that public state only. It builds `KB_t = CNF(revealed clues) AND known-verdict unit clauses`, asks DPLL under complementary assumptions, and classifies every unresolved character as criminal, innocent, unknown, or inconsistent. The UI's Hint and Auto Solve use this same agent.

`griductive.cnf.CNFEncoder` has a deterministic primary-variable map (alphabetical display names) and separate auxiliary-variable count. All present encodings use direct clauses and therefore create zero auxiliary variables. Counting constraints use the standard subset encoding: at-most `k` forbids every `(k+1)`-criminal subset, and at-least `k` forbids every `(n-k+1)`-innocent subset.

`griductive.dpll.DPLLSolver` implements unit propagation, conflict detection, deterministic branching, recursive backtracking, complete models, and statistics.

## Puzzle schema in code

`griductive/puzzles.py` generates a fresh case on every launch and whenever the player presses New Random Case. Rows and columns are selected independently from 3 through 5, so all nine rectangular/square layouts are possible. The roster, portrait positions, hidden statuses, clue types, reveal paths, and two initially public cards are shuffled. Each seed is shown in the UI for reproducibility. Two seeded reveal chains guarantee a unique full solution and a progressive no-guess path; clue meaning is never handwritten as a puzzle-specific CNF formula.

Supported core clues are `FACT`, `SAME`, `DIFFERENT`, `EXACTLY`, `AT_LEAST`, and `AT_MOST`. Extensions are `PARITY` (even/odd criminal count) and `COUNT_COMPARE` (`EQ`, `GT`, or `LT` between two region counts).

`griductive.regions` provides the required deterministic region constructors: `row(column_count, index)`, `column(row_count, index)`, `neighbors(row_count, cell, column_count)`, and `explicit(cells)`. All encode to the same validated list of distinct cell identifiers, so rectangular boards use the same CNF encoder and GUI-highlighting path.

## Tests

The tests cover semantic evaluation, CNF agreement with semantic evaluation, DPLL SAT/UNSAT, all nine board dimensions, random-case uniqueness, seed reproducibility, progressive auto-solving, and the public-state boundary.

## Experiments

Run `python experiments.py` to regenerate `experiment_results.csv`. The committed CSV is a baseline run; runtimes vary by computer. It records the initial public-KB clause count and cumulative Auto Solve SAT/DPLL statistics for reproducible seeded 3x3, 3x4, 4x5, and 5x5 random cases. Fixed seeds are used only so report comparisons remain fair; the player-facing game always generates a fresh case.
