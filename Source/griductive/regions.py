"""Deterministic constructors for the four required Griductive region forms."""
from __future__ import annotations


def cell(column: int, row: int) -> str:
    return f"{chr(65 + column)}{row + 1}"


def row(column_count: int, row_index: int) -> tuple[str, ...]:
    if not 0 <= row_index < 5:
        raise ValueError("row index outside board")
    if not 3 <= column_count <= 5:
        raise ValueError("column count must be between 3 and 5")
    return tuple(cell(column, row_index) for column in range(column_count))


def column(row_count: int, column_index: int) -> tuple[str, ...]:
    if not 0 <= column_index < 5:
        raise ValueError("column index outside board")
    if not 3 <= row_count <= 5:
        raise ValueError("row count must be between 3 and 5")
    return tuple(cell(column_index, row_index) for row_index in range(row_count))


def neighbors(rows: int, center: str, columns: int | None = None) -> tuple[str, ...]:
    columns = rows if columns is None else columns
    column, row = ord(center[0]) - 65, int(center[1:]) - 1
    if not 0 <= column < columns or not 0 <= row < rows:
        raise ValueError("center outside board")
    return tuple(
        cell(next_column, next_row)
        for next_row in range(max(0, row - 1), min(rows, row + 2))
        for next_column in range(max(0, column - 1), min(columns, column + 2))
        if (next_column, next_row) != (column, row)
    )


def explicit(cells: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    result = tuple(cells)
    if not result or len(set(result)) != len(result):
        raise ValueError("an explicit region must contain distinct cells")
    return result
