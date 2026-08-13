from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Mapping, Sequence

from .cnf import Clause
from .models import SolverStats


@dataclass(frozen=True)
class SolveResult:
    satisfiable: bool
    assignment: Mapping[int, bool] | None
    stats: SolverStats


class DPLLSolver:
    """Deterministic DPLL with unit propagation and chronological backtracking."""

    def solve(self, clauses: Sequence[Clause], variable_count: int, assumptions: Sequence[int] = ()) -> SolveResult:
        self.decisions = self.propagations = self.backtracks = 0
        start = perf_counter()
        assignment: dict[int, bool] = {}
        for literal in assumptions:
            if not self._assign(assignment, literal):
                return self._result(False, None, start)
        model = self._search(tuple(clauses), variable_count, assignment)
        return self._result(model is not None, model, start)

    def _result(self, satisfiable: bool, assignment: dict[int, bool] | None, start: float) -> SolveResult:
        complete = None
        if assignment is not None:
            complete = dict(assignment)
        return SolveResult(satisfiable, complete, SolverStats(1, self.decisions, self.propagations, self.backtracks, (perf_counter() - start) * 1000))

    def _search(self, clauses: tuple[Clause, ...], variable_count: int, assignment: dict[int, bool]) -> dict[int, bool] | None:
        state = dict(assignment)
        if not self._propagate(clauses, state):
            return None
        if len(state) == variable_count:
            return state
        variable = next(index for index in range(1, variable_count + 1) if index not in state)
        self.decisions += 1
        for value in (True, False):
            child = dict(state)
            child[variable] = value
            result = self._search(clauses, variable_count, child)
            if result is not None:
                return result
            self.backtracks += 1
        return None

    def _propagate(self, clauses: tuple[Clause, ...], assignment: dict[int, bool]) -> bool:
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                status, unit = self._clause_state(clause, assignment)
                if status == "CONFLICT":
                    return False
                if status == "UNIT":
                    if not self._assign(assignment, unit):
                        return False
                    self.propagations += 1
                    changed = True
        return True

    @staticmethod
    def _clause_state(clause: Clause, assignment: Mapping[int, bool]) -> tuple[str, int | None]:
        unresolved: list[int] = []
        for literal in clause:
            value = assignment.get(abs(literal))
            if value is None:
                unresolved.append(literal)
            elif value == (literal > 0):
                return "SAT", None
        if not unresolved:
            return "CONFLICT", None
        if len(unresolved) == 1:
            return "UNIT", unresolved[0]
        return "OPEN", None

    @staticmethod
    def _assign(assignment: dict[int, bool], literal: int) -> bool:
        variable, value = abs(literal), literal > 0
        current = assignment.get(variable)
        if current is not None and current != value:
            return False
        assignment[variable] = value
        return True
