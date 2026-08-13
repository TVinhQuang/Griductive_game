"""Run the report-ready benchmark table on the same 3x3, 4x4, and 5x5 puzzle set."""
from __future__ import annotations

import csv
from pathlib import Path

from griductive.agent import LogicAgent
from griductive.cnf import CNFEncoder
from griductive.engine import GameEngine
from griductive.puzzles import benchmark_puzzles


def main() -> None:
    rows = []
    for puzzle in benchmark_puzzles():
        engine = GameEngine(puzzle)
        agent = LogicAgent()
        initial = CNFEncoder(puzzle.characters).encode_public(engine.public_state())
        while not engine.is_solved():
            result, _ = engine.auto_step(agent)
            if result.value != "ACCEPTED":
                raise RuntimeError(f"{puzzle.id} stopped at {result.value}")
        stats = [item.stats for item in engine.trace]
        rows.append({
            "puzzle": puzzle.title,
            "primary_variables": initial.primary_variables,
            "auxiliary_variables": initial.auxiliary_variables,
            "initial_cnf_clauses": len(initial.clauses),
            "sat_calls": sum(item.sat_calls for item in stats),
            "decisions": sum(item.decisions for item in stats),
            "propagations": sum(item.propagations for item in stats),
            "backtracks": sum(item.backtracks for item in stats),
            "deduction_steps": len(engine.trace),
            "runtime_ms": round(sum(item.runtime_ms for item in stats), 3),
        })
    destination = Path(__file__).with_name("experiment_results.csv")
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row)
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
