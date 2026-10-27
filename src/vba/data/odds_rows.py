"""Turn one CSV row into long-format `odds` records."""

from vba.data.odds_mapping import ODDS_COLUMNS


def _to_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_odds(row: dict[str, str], match_id: str) -> list[dict[str, object]]:
    """Build one record per odds cell present in the row.

    Cells that are empty, not numeric or not valid decimal odds (<= 1.0) are
    skipped, as are handicap odds whose line is missing.
    """
    records: list[dict[str, object]] = []
    for column, spec in ODDS_COLUMNS.items():
        price = _to_float(row.get(column))
        if price is None or price <= 1.0:
            continue

        line = spec.line
        if spec.line_column is not None:
            line = _to_float(row.get(spec.line_column))
            if line is None:
                continue

        records.append(
            {
                "match_id": match_id,
                "bookmaker": spec.bookmaker,
                "market": spec.market,
                "selection": spec.selection,
                "line": line,
                "is_closing": spec.is_closing,
                "odds": price,
            }
        )
    return records
