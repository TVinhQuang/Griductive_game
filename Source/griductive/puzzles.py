from __future__ import annotations

from random import Random, SystemRandom

from .models import Character, Clue, ClueKind, Puzzle, Status
from .regions import explicit


NAMES = (
    "Ada", "Binh", "Chi", "Duy", "Emi", "Finn", "Gia", "Hana", "Ivy", "Jae",
    "Khan", "Linh", "Minh", "Nora", "Owen", "Phuc", "Quynh", "Rin", "Son", "Trang",
    "Uma", "Vy", "Will", "Xuan", "Yen",
)
PROFESSIONS = (
    "Architect", "Botanist", "Chef", "Doctor", "Engineer", "Forensic Artist", "Geologist",
    "Historian", "Illustrator", "Journalist", "Keeper", "Librarian", "Musician", "Nurse",
    "Oceanographer", "Pilot", "Researcher", "Scientist", "Teacher", "Urbanist", "Violinist",
    "Writer", "Xylophonist", "Yacht Captain", "Zoologist",
)
CLUE_CYCLE = (
    ClueKind.FACT, ClueKind.SAME, ClueKind.DIFFERENT, ClueKind.EXACTLY,
    ClueKind.AT_LEAST, ClueKind.AT_MOST, ClueKind.PARITY, ClueKind.COUNT_COMPARE,
)


def _cells(rows: int, columns: int) -> tuple[str, ...]:
    return tuple(f"{chr(65 + column)}{row + 1}" for row in range(rows) for column in range(columns))


def _chain_clue(owner: str, target: str, owner_status: Status, target_status: Status,
                kind: ClueKind, index: int) -> Clue:
    clue_id = f"CLUE-{index + 1:02d}"
    if kind is ClueKind.FACT:
        return Clue(clue_id, owner, kind, targets=(target,), status=target_status)
    if kind is ClueKind.SAME:
        relation = ClueKind.SAME if owner_status is target_status else ClueKind.DIFFERENT
        return Clue(clue_id, owner, relation, targets=(target, owner))
    if kind is ClueKind.DIFFERENT:
        relation = ClueKind.DIFFERENT if owner_status is not target_status else ClueKind.SAME
        return Clue(clue_id, owner, relation, targets=(target, owner))
    if kind is ClueKind.EXACTLY:
        return Clue(clue_id, owner, kind, region=explicit((target,)), k=int(target_status is Status.CRIMINAL))
    if kind is ClueKind.AT_LEAST:
        if target_status is Status.CRIMINAL:
            return Clue(clue_id, owner, kind, region=explicit((target,)), k=1)
        return Clue(clue_id, owner, ClueKind.AT_MOST, region=explicit((target,)), k=0)
    if kind is ClueKind.AT_MOST:
        if target_status is Status.INNOCENT:
            return Clue(clue_id, owner, kind, region=explicit((target,)), k=0)
        return Clue(clue_id, owner, ClueKind.AT_LEAST, region=explicit((target,)), k=1)
    if kind is ClueKind.PARITY:
        return Clue(clue_id, owner, kind, region=(target,),
                    parity="ODD" if target_status is Status.CRIMINAL else "EVEN")
    comparison = "EQ" if target_status is owner_status else (
        "GT" if target_status is Status.CRIMINAL else "LT"
    )
    return Clue(clue_id, owner, ClueKind.COUNT_COMPARE, region=(target,),
                region_b=(owner,), comparison=comparison)


def generate_random_case(seed: int | None = None, rows: int | None = None,
                         columns: int | None = None) -> Puzzle:
    """Create a reproducible unique, progressive no-guess puzzle on a 3..5 by 3..5 board."""
    actual_seed = seed if seed is not None else SystemRandom().randrange(1, 2**31)
    rng = Random(actual_seed)
    row_count = rows if rows is not None else rng.randint(3, 5)
    column_count = columns if columns is not None else rng.randint(3, 5)
    if not 3 <= row_count <= 5 or not 3 <= column_count <= 5:
        raise ValueError("Random case dimensions must both be between 3 and 5")

    cells = _cells(row_count, column_count)
    count = len(cells)

    # A shuffled roster makes both the displayed people and their board positions vary by seed.
    roster = list(range(len(NAMES)))
    rng.shuffle(roster)
    chosen = roster[:count]
    characters = tuple(
        Character(cell, NAMES[profile], PROFESSIONS[profile], profile)
        for cell, profile in zip(cells, chosen)
    )

    values = [rng.choice((True, False)) for _ in cells]
    if all(values) or not any(values):
        values[0], values[-1] = True, False
    solution = {cell: Status.from_boolean(value) for cell, value in zip(cells, values)}

    # Two independently shuffled reveal chains begin at the two face-up cards. This construction
    # guarantees every hidden card eventually becomes entailed without consulting hidden labels.
    reveal_order = list(cells)
    rng.shuffle(reveal_order)
    roots = (reveal_order[0], reveal_order[1])
    paths = [[roots[0]], [roots[1]]]
    for index, cell in enumerate(reveal_order[2:]):
        paths[index % 2].append(cell)
    next_target: dict[str, str] = {}
    for path in paths:
        for owner, target in zip(path, path[1:]):
            next_target[owner] = target
        next_target[path[-1]] = path[0]

    kinds = [CLUE_CYCLE[index % len(CLUE_CYCLE)] for index in range(count)]
    rng.shuffle(kinds)
    clues = {
        owner: _chain_clue(owner, next_target[owner], solution[owner], solution[next_target[owner]], kinds[index], index)
        for index, owner in enumerate(cells)
    }
    case_code = f"{actual_seed:08X}"
    return Puzzle(
        f"random-{row_count}x{column_count}-{case_code}",
        f"Random Case {row_count}×{column_count}",
        row_count,
        column_count,
        characters,
        clues,
        solution,
        roots,
        actual_seed,
    )


def benchmark_puzzles() -> tuple[Puzzle, ...]:
    """Stable random cases used only for repeatable tests and report experiments."""
    return (
        generate_random_case(3003, 3, 3),
        generate_random_case(3004, 3, 4),
        generate_random_case(4005, 4, 5),
        generate_random_case(5005, 5, 5),
    )
