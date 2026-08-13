from __future__ import annotations

from .agent import LogicAgent
from .clues import evaluate, validate
from .cnf import CNFEncoder
from .dpll import DPLLSolver
from .models import (
    Deduction,
    PublicState,
    Puzzle,
    SolverStats,
    Status,
    SubmissionResult,
    TraceEntry,
    Verdict,
)


class GameEngine:
    """Owns private puzzle data. It exposes a deliberately reduced public state to agents."""

    def __init__(self, puzzle: Puzzle):
        self.puzzle = puzzle
        self._validate_puzzle()
        self.restart()

    def restart(self) -> None:
        self._known: dict[str, Status] = {cell: self.puzzle.solution[cell] for cell in self.puzzle.initially_revealed}
        self._revealed: set[str] = set(self.puzzle.initially_revealed)
        self.trace: list[TraceEntry] = []

    def public_state(self) -> PublicState:
        return PublicState(
            self.puzzle.id,
            self.puzzle.rows,
            self.puzzle.columns,
            self.puzzle.characters,
            tuple(self.puzzle.clues[cell] for cell in sorted(self._revealed, key=self._row_major_key)),
            dict(self._known),
        )

    def submit(self, cell: str, proposed: Status, agent: LogicAgent) -> SubmissionResult:
        if cell in self._known:
            return SubmissionResult.ALREADY_SOLVED
        if cell not in self.puzzle.solution:
            raise ValueError(f"Unknown cell: {cell}")
        classification = agent.classify_all(self.public_state())
        return self._submit_classification(cell, proposed, classification)

    def _submit_classification(self, cell: str, proposed: Status, classification) -> SubmissionResult:
        deduction = classification.verdicts[cell]
        if deduction.verdict is Verdict.INCONSISTENT:
            return SubmissionResult.INCONSISTENT
        if deduction.verdict is Verdict.UNKNOWN:
            return SubmissionResult.NOT_PROVABLE
        forced = Status(deduction.verdict.value)
        if forced is not proposed:
            return SubmissionResult.CONTRADICTED
        # Private data is used only after public logic has accepted the verdict.
        if self.puzzle.solution[cell] is not forced:
            raise RuntimeError("Puzzle validation failure: an entailed verdict differs from the private solution")
        self._known[cell] = forced
        self._revealed.add(cell)
        self.trace.append(TraceEntry(
            len(self.trace) + 1,
            tuple(clue.id for clue in self.public_state().revealed_clues if clue.owner != cell),
            cell,
            deduction.verdict,
            deduction.queries,
            self.puzzle.clues[cell].id,
            classification.stats,
        ))
        return SubmissionResult.ACCEPTED

    def auto_step(self, agent: LogicAgent) -> tuple[SubmissionResult, Deduction | None]:
        classification = agent.classify_all(self.public_state())
        if classification.inconsistent:
            return SubmissionResult.INCONSISTENT, next(iter(classification.verdicts.values()), None)
        next_item = next((classification.verdicts[cell] for cell in self._row_major_cells_from_state()
                          if cell in classification.verdicts and classification.verdicts[cell].verdict in (Verdict.CRIMINAL, Verdict.INNOCENT)), None)
        if next_item is None:
            return SubmissionResult.NOT_PROVABLE, None
        result = self._submit_classification(next_item.cell, Status(next_item.verdict.value), classification)
        return result, next_item

    def is_solved(self) -> bool:
        return len(self._known) == len(self.puzzle.characters)

    def uniqueness_check(self) -> tuple[bool, SolverStats]:
        """Uses all clues, finds one primary model, then blocks it and solves again."""
        full = PublicState(self.puzzle.id, self.puzzle.rows, self.puzzle.columns,
                           self.puzzle.characters, tuple(self.puzzle.clues.values()), {})
        encoded = CNFEncoder(full.characters).encode_public(full)
        first = DPLLSolver().solve(encoded.clauses, encoded.primary_variables)
        if not first.satisfiable:
            return False, first.stats
        blocking = tuple(-index if first.assignment[index] else index for index in range(1, encoded.primary_variables + 1))
        second = DPLLSolver().solve(encoded.clauses + (blocking,), encoded.primary_variables)
        return not second.satisfiable, first.stats.plus(second.stats)

    def _validate_puzzle(self) -> None:
        cells = {character.cell for character in self.puzzle.characters}
        if not 3 <= self.puzzle.rows <= 5 or not 3 <= self.puzzle.columns <= 5:
            raise ValueError("Puzzle dimensions must both be between 3 and 5")
        if len(cells) != self.puzzle.rows * self.puzzle.columns:
            raise ValueError("Puzzle board does not have rows*columns unique characters")
        expected = {
            f"{chr(65 + column)}{row + 1}"
            for row in range(self.puzzle.rows)
            for column in range(self.puzzle.columns)
        }
        if cells != expected:
            raise ValueError("Puzzle cells do not match its rectangular dimensions")
        if set(self.puzzle.clues) != cells or set(self.puzzle.solution) != cells:
            raise ValueError("Puzzle clues and solution must cover every cell")
        for cell, clue in self.puzzle.clues.items():
            if clue.owner != cell:
                raise ValueError(f"Clue owner mismatch at {cell}")
            validate(clue, cells)
            if not evaluate(clue, self.puzzle.solution):
                raise ValueError(f"{clue.id} is false in puzzle solution")
        if not set(self.puzzle.initially_revealed).issubset(cells):
            raise ValueError("Invalid initially revealed card")

    @staticmethod
    def _row_major_key(cell: str) -> tuple[int, str]:
        return int(cell[1:]), cell[0]

    def _row_major_cells_from_state(self) -> list[str]:
        return sorted((character.cell for character in self.puzzle.characters), key=self._row_major_key)
