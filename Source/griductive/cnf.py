from __future__ import annotations

from itertools import combinations, product
from dataclasses import dataclass
from typing import Iterable, Mapping

from .clues import evaluate, validate
from .models import Character, Clue, ClueKind, PublicState, Status

Clause = tuple[int, ...]


@dataclass(frozen=True)
class EncodedKB:
    clauses: tuple[Clause, ...]
    variable_map: Mapping[str, int]
    primary_variables: int
    auxiliary_variables: int


class CNFEncoder:
    """Reusable direct CNF encoder. Positive literal means CRIMINAL."""

    def __init__(self, characters: Iterable[Character]):
        ordered = sorted(characters, key=lambda item: (item.name.casefold(), item.cell))
        self.variable_map = {character.cell: index + 1 for index, character in enumerate(ordered)}
        self.cells = set(self.variable_map)

    def encode_public(self, state: PublicState) -> EncodedKB:
        clauses: list[Clause] = []
        for clue in state.revealed_clues:
            clauses.extend(self.encode_clue(clue))
        for cell, status in state.known_verdicts.items():
            clauses.append((self.literal(cell, status),))
        return EncodedKB(tuple(clauses), self.variable_map, len(self.variable_map), 0)

    def encode_clue(self, clue: Clue) -> list[Clause]:
        validate(clue, self.cells)
        lit = self.literal
        if clue.kind is ClueKind.FACT:
            return [(lit(clue.targets[0], clue.status),)]
        if clue.kind is ClueKind.SAME:
            a, b = (self.variable_map[cell] for cell in clue.targets)
            return [(-a, b), (a, -b)]
        if clue.kind is ClueKind.DIFFERENT:
            a, b = (self.variable_map[cell] for cell in clue.targets)
            return [(a, b), (-a, -b)]
        if clue.kind is ClueKind.EXACTLY:
            return self._at_most(clue.region, clue.k) + self._at_least(clue.region, clue.k)
        if clue.kind is ClueKind.AT_LEAST:
            return self._at_least(clue.region, clue.k)
        if clue.kind is ClueKind.AT_MOST:
            return self._at_most(clue.region, clue.k)
        # The two extensions are direct truth-table encodings over their referenced cells.
        # This is intentionally bounded for a classroom board and avoids opaque library code.
        refs = tuple(dict.fromkeys(clue.region + clue.region_b))
        if clue.kind is ClueKind.PARITY:
            refs = clue.region
        if len(refs) > 12:
            raise ValueError(f"{clue.id}: direct extension encoding supports at most 12 referenced cells")
        return self._semantic_truth_table(clue, refs)

    def literal(self, cell: str, status: Status) -> int:
        var = self.variable_map[cell]
        return var if status is Status.CRIMINAL else -var

    def _at_most(self, region: tuple[str, ...], k: int) -> list[Clause]:
        if k == len(region):
            return []
        return [tuple(-self.variable_map[cell] for cell in subset) for subset in combinations(region, k + 1)]

    def _at_least(self, region: tuple[str, ...], k: int) -> list[Clause]:
        if k == 0:
            return []
        # Any n-k+1 cells cannot all be innocent.
        subset_size = len(region) - k + 1
        return [tuple(self.variable_map[cell] for cell in subset) for subset in combinations(region, subset_size)]

    def _semantic_truth_table(self, clue: Clue, refs: tuple[str, ...]) -> list[Clause]:
        clauses: list[Clause] = []
        for values in product((False, True), repeat=len(refs)):
            assignment = {cell: Status.from_boolean(value) for cell, value in zip(refs, values)}
            if not evaluate(clue, assignment):
                # Block this exact invalid assignment.
                clauses.append(tuple(-self.variable_map[cell] if value else self.variable_map[cell] for cell, value in zip(refs, values)))
        return clauses
