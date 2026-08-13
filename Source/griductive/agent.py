from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .cnf import CNFEncoder, EncodedKB
from .dpll import DPLLSolver
from .models import Deduction, PublicState, SolverStats, Status, Verdict


@dataclass(frozen=True)
class Classification:
    verdicts: Mapping[str, Deduction]
    encoded: EncodedKB
    inconsistent: bool
    stats: SolverStats


class LogicAgent:
    """A public-knowledge-only SAT agent. It has no Puzzle or GameEngine reference."""

    def classify_all(self, state: PublicState) -> Classification:
        encoder = CNFEncoder(state.characters)
        encoded = encoder.encode_public(state)
        base = DPLLSolver().solve(encoded.clauses, encoded.primary_variables)
        if not base.satisfiable:
            return Classification(
                {cell: Deduction(cell, Verdict.INCONSISTENT, ("KB = UNSAT",), base.stats)
                 for cell in encoder.variable_map if cell not in state.known_verdicts},
                encoded,
                True,
                base.stats,
            )
        deductions: dict[str, Deduction] = {}
        total_stats = base.stats
        for cell in self._row_major_cells(state):
            if cell in state.known_verdicts:
                continue
            variable = encoded.variable_map[cell]
            criminal_test = DPLLSolver().solve(encoded.clauses, encoded.primary_variables, (-variable,))
            innocent_test = DPLLSolver().solve(encoded.clauses, encoded.primary_variables, (variable,))
            stats = criminal_test.stats.plus(innocent_test.stats)
            total_stats = total_stats.plus(stats)
            queries = (
                f"KB & NOT {cell} = {'SAT' if criminal_test.satisfiable else 'UNSAT'}",
                f"KB & {cell} = {'SAT' if innocent_test.satisfiable else 'UNSAT'}",
            )
            if not criminal_test.satisfiable:
                verdict = Verdict.CRIMINAL
            elif not innocent_test.satisfiable:
                verdict = Verdict.INNOCENT
            else:
                verdict = Verdict.UNKNOWN
            deductions[cell] = Deduction(cell, verdict, queries, stats)
        return Classification(deductions, encoded, False, total_stats)

    def next_forced(self, state: PublicState) -> Deduction | None:
        classification = self.classify_all(state)
        if classification.inconsistent:
            return next(iter(classification.verdicts.values()), None)
        for cell in self._row_major_cells(state):
            item = classification.verdicts.get(cell)
            if item and item.verdict in (Verdict.CRIMINAL, Verdict.INNOCENT):
                return item
        return None

    @staticmethod
    def _row_major_cells(state: PublicState) -> list[str]:
        return sorted((character.cell for character in state.characters), key=lambda cell: (int(cell[1:]), cell[0]))
