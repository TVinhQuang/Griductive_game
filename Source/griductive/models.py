from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class Status(str, Enum):
    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"

    @property
    def boolean(self) -> bool:
        return self is Status.CRIMINAL

    @classmethod
    def from_boolean(cls, value: bool) -> "Status":
        return cls.CRIMINAL if value else cls.INNOCENT


class ClueKind(str, Enum):
    FACT = "FACT"
    SAME = "SAME"
    DIFFERENT = "DIFFERENT"
    EXACTLY = "EXACTLY"
    AT_LEAST = "AT_LEAST"
    AT_MOST = "AT_MOST"
    PARITY = "PARITY"
    COUNT_COMPARE = "COUNT_COMPARE"


class Verdict(str, Enum):
    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"
    UNKNOWN = "UNKNOWN"
    INCONSISTENT = "INCONSISTENT"


class SubmissionResult(str, Enum):
    ACCEPTED = "ACCEPTED"
    NOT_PROVABLE = "NOT_PROVABLE"
    CONTRADICTED = "CONTRADICTED"
    INCONSISTENT = "INCONSISTENT"
    ALREADY_SOLVED = "ALREADY_SOLVED"


@dataclass(frozen=True)
class Character:
    cell: str
    name: str
    profession: str
    portrait_index: int = 0


@dataclass(frozen=True)
class Clue:
    id: str
    owner: str
    kind: ClueKind
    targets: tuple[str, ...] = ()
    status: Status | None = None
    region: tuple[str, ...] = ()
    k: int | None = None
    parity: str | None = None
    region_b: tuple[str, ...] = ()
    comparison: str | None = None


@dataclass(frozen=True)
class Puzzle:
    id: str
    title: str
    rows: int
    columns: int
    characters: tuple[Character, ...]
    clues: Mapping[str, Clue]
    solution: Mapping[str, Status]
    initially_revealed: tuple[str, ...]
    seed: int = 0

    @property
    def cell_count(self) -> int:
        return self.rows * self.columns


@dataclass(frozen=True)
class PublicState:
    puzzle_id: str
    rows: int
    columns: int
    characters: tuple[Character, ...]
    revealed_clues: tuple[Clue, ...]
    known_verdicts: Mapping[str, Status]


@dataclass(frozen=True)
class SolverStats:
    sat_calls: int = 0
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime_ms: float = 0.0

    def plus(self, other: "SolverStats") -> "SolverStats":
        return SolverStats(
            self.sat_calls + other.sat_calls,
            self.decisions + other.decisions,
            self.propagations + other.propagations,
            self.backtracks + other.backtracks,
            self.runtime_ms + other.runtime_ms,
        )


@dataclass(frozen=True)
class Deduction:
    cell: str
    verdict: Verdict
    queries: tuple[str, ...]
    stats: SolverStats


@dataclass(frozen=True)
class TraceEntry:
    step: int
    active_clue_ids: tuple[str, ...]
    cell: str
    verdict: Verdict
    sat_queries: tuple[str, ...]
    revealed_clue_id: str
    stats: SolverStats
