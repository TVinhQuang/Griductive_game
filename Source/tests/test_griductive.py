from __future__ import annotations

import sys
from itertools import product
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from griductive.agent import LogicAgent
from griductive.clues import evaluate
from griductive.cnf import CNFEncoder
from griductive.dpll import DPLLSolver
from griductive.engine import GameEngine
from griductive.models import PublicState, Status
from griductive.puzzles import benchmark_puzzles, generate_random_case
from griductive.regions import column, explicit, neighbors, row


class GriductiveTests(unittest.TestCase):
    def test_dpll_sat_and_unsat(self) -> None:
        self.assertTrue(DPLLSolver().solve(((1, 2), (-1, 2)), 2).satisfiable)
        self.assertFalse(DPLLSolver().solve(((1,), (-1,)), 1).satisfiable)

    def test_clues_true_in_hidden_solution(self) -> None:
        for puzzle in benchmark_puzzles():
            for clue in puzzle.clues.values():
                self.assertTrue(evaluate(clue, puzzle.solution), clue.id)

    def test_cnf_matches_semantics_for_each_clue(self) -> None:
        # Every supplied clue references few cells, so exhaustively compare its CNF with its direct evaluator.
        for puzzle in benchmark_puzzles():
            encoder = CNFEncoder(puzzle.characters)
            reverse_map = {var: cell for cell, var in encoder.variable_map.items()}
            for clue in puzzle.clues.values():
                clauses = encoder.encode_clue(clue)
                refs = sorted(set(clue.targets + clue.region + clue.region_b))
                for values in product((False, True), repeat=len(refs)):
                    assignment = {cell: Status.from_boolean(value) for cell, value in zip(refs, values)}
                    cnf_value = all(
                        any(assignment[reverse_map[abs(literal)]].boolean == (literal > 0) for literal in clause)
                        for clause in clauses
                    )
                    self.assertEqual(evaluate(clue, assignment), cnf_value, clue.id)

    def test_random_cases_unique_and_autosolve_without_guessing(self) -> None:
        agent = LogicAgent()
        seed = 100
        for rows in range(3, 6):
            for columns in range(3, 6):
                puzzle = generate_random_case(seed, rows, columns)
                engine = GameEngine(puzzle)
                unique, _ = engine.uniqueness_check()
                self.assertTrue(unique, puzzle.id)
                while not engine.is_solved():
                    result, _ = engine.auto_step(agent)
                    self.assertEqual(result.value, "ACCEPTED", puzzle.id)
                self.assertEqual(len(engine.trace), rows * columns - 2)
                seed += 1

    def test_agent_receives_no_solution_or_hidden_clues(self) -> None:
        engine = GameEngine(generate_random_case(8080, 5, 4))
        state = engine.public_state()
        self.assertFalse(hasattr(state, "solution"))
        self.assertEqual(len(state.revealed_clues), 2)
        self.assertEqual(len(state.known_verdicts), 2)
        self.assertLess(len(state.revealed_clues), len(state.characters))

    def test_random_case_is_reproducible_and_roster_is_shuffled(self) -> None:
        first = generate_random_case(424242, 3, 5)
        second = generate_random_case(424242, 3, 5)
        other = generate_random_case(424243, 3, 5)
        self.assertEqual(first, second)
        self.assertNotEqual(first.characters, other.characters)
        self.assertEqual((first.rows, first.columns, len(first.characters)), (3, 5, 15))

    def test_required_region_constructors(self) -> None:
        self.assertEqual(row(3, 1), ("A2", "B2", "C2"))
        self.assertEqual(column(3, 1), ("B1", "B2", "B3"))
        self.assertEqual(neighbors(3, "B2"), ("A1", "B1", "C1", "A2", "C2", "A3", "B3", "C3"))
        self.assertEqual(neighbors(3, "A1"), ("B1", "A2", "B2"))
        self.assertEqual(neighbors(3, "D2", 5), ("C1", "D1", "E1", "C2", "E2", "C3", "D3", "E3"))
        self.assertEqual(explicit(("A1", "C3")), ("A1", "C3"))


if __name__ == "__main__":
    unittest.main()
