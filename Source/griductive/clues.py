from __future__ import annotations

from itertools import chain
from typing import Mapping

from .models import Clue, ClueKind, Status


def all_references(clue: Clue) -> tuple[str, ...]:
    """Every board cell that should be highlighted for a clue."""
    return tuple(dict.fromkeys(chain(clue.targets, clue.region, clue.region_b)))


def describe(clue: Clue, labels: Mapping[str, str] | None = None) -> str:
    def show(cell: str) -> str:
        return labels.get(cell, cell) if labels else cell

    def group(cells: tuple[str, ...]) -> str:
        return ", ".join(show(c) for c in cells)

    if clue.kind is ClueKind.FACT:
        return f"{show(clue.targets[0])} is {clue.status.value}."
    if clue.kind is ClueKind.SAME:
        return f"{show(clue.targets[0])} and {show(clue.targets[1])} have the same status."
    if clue.kind is ClueKind.DIFFERENT:
        return f"{show(clue.targets[0])} and {show(clue.targets[1])} have different statuses."
    if clue.kind is ClueKind.EXACTLY:
        return f"Exactly {clue.k} criminal(s) among: {group(clue.region)}."
    if clue.kind is ClueKind.AT_LEAST:
        return f"At least {clue.k} criminal(s) among: {group(clue.region)}."
    if clue.kind is ClueKind.AT_MOST:
        return f"At most {clue.k} criminal(s) among: {group(clue.region)}."
    if clue.kind is ClueKind.PARITY:
        return f"The number of criminals among {group(clue.region)} is {clue.parity}."
    return f"Criminal count in ({group(clue.region)}) is {clue.comparison} count in ({group(clue.region_b)})."


def validate(clue: Clue, cells: set[str]) -> None:
    refs = all_references(clue)
    if any(cell not in cells for cell in refs):
        raise ValueError(f"{clue.id}: unknown cell reference")
    if clue.kind is ClueKind.FACT:
        if len(clue.targets) != 1 or clue.status is None:
            raise ValueError(f"{clue.id}: FACT requires one target and status")
    elif clue.kind in (ClueKind.SAME, ClueKind.DIFFERENT):
        if len(clue.targets) != 2 or clue.targets[0] == clue.targets[1]:
            raise ValueError(f"{clue.id}: binary clue requires two distinct targets")
    elif clue.kind in (ClueKind.EXACTLY, ClueKind.AT_LEAST, ClueKind.AT_MOST):
        if not clue.region or len(set(clue.region)) != len(clue.region) or clue.k is None or not 0 <= clue.k <= len(clue.region):
            raise ValueError(f"{clue.id}: invalid counting clue")
    elif clue.kind is ClueKind.PARITY:
        if not clue.region or clue.parity not in ("EVEN", "ODD"):
            raise ValueError(f"{clue.id}: invalid parity clue")
    elif clue.kind is ClueKind.COUNT_COMPARE:
        if not clue.region or not clue.region_b or clue.comparison not in ("EQ", "GT", "LT"):
            raise ValueError(f"{clue.id}: invalid count comparison")


def evaluate(clue: Clue, assignment: Mapping[str, Status]) -> bool:
    criminal_count = lambda region: sum(assignment[cell] is Status.CRIMINAL for cell in region)
    if clue.kind is ClueKind.FACT:
        return assignment[clue.targets[0]] is clue.status
    if clue.kind is ClueKind.SAME:
        return assignment[clue.targets[0]] is assignment[clue.targets[1]]
    if clue.kind is ClueKind.DIFFERENT:
        return assignment[clue.targets[0]] is not assignment[clue.targets[1]]
    count = criminal_count(clue.region)
    if clue.kind is ClueKind.EXACTLY:
        return count == clue.k
    if clue.kind is ClueKind.AT_LEAST:
        return count >= clue.k
    if clue.kind is ClueKind.AT_MOST:
        return count <= clue.k
    if clue.kind is ClueKind.PARITY:
        return (count % 2 == 0) == (clue.parity == "EVEN")
    right = criminal_count(clue.region_b)
    return {"EQ": count == right, "GT": count > right, "LT": count < right}[clue.comparison]
