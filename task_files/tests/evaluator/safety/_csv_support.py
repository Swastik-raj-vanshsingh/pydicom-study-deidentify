"""Shared helper for the two crosswalk-neutralisation requirements."""

from __future__ import annotations

FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")


def dangerous_cells(rows) -> list[str]:
    """Data cells a spreadsheet would read as a formula rather than as text."""
    found = []
    for row in rows[1:]:
        for cell in row:
            if cell[:1] in FORMULA_LEAD:
                found.append(cell)
    return found


def cell_containing(rows, marker: str) -> str | None:
    for row in rows[1:]:
        for cell in row:
            if marker in cell:
                return cell
    return None
