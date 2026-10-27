"""Single place that maps football-data.co.uk odds columns to the long `odds` format.

Each CSV column resolves to (bookmaker, market, selection, is_closing) plus the
line of the bet. To support a new bookmaker or market, add it to the tables below;
nothing else in the ingestion needs to change.

Column naming in the CSVs:

- 1X2 opening:        {prefix}H / {prefix}D / {prefix}A          e.g. B365H, PSD, AvgA
- 1X2 closing:        {prefix}CH / {prefix}CD / {prefix}CA       e.g. PSCH, MaxCD
- Over/under opening: {prefix}>2.5 / {prefix}<2.5                e.g. B365>2.5, P<2.5
- Over/under closing: {prefix}C>2.5 / {prefix}C<2.5              e.g. PC>2.5
- Asian handicap:     {prefix}AHH / {prefix}AHA (opening, line in column AHh)
                      {prefix}CAHH / {prefix}CAHA (closing, line in column AHCh)

Prefixes are not consistent between markets (Pinnacle is PS in 1X2 but P in
over/under and handicap), hence one table per market family.

The handicap `line` is stored exactly as in the CSV, which is the handicap of the
home team, for both the home and the away selection.

Legacy format (2018-19 only): market max/average are called BbMx*/BbAv* and the
handicap line is BbAHh. They map to the same market_max / market_avg bookmakers.
Closing odds in that season exist only for Pinnacle 1X2 (PSC*).
"""

from dataclasses import dataclass

# Pseudo-bookmakers for the market-wide aggregates football-data computes.
MARKET_MAX = "market_max"
MARKET_AVG = "market_avg"

# prefix -> bookmaker, per market family.
BOOKMAKERS_1X2 = {
    "B365": "bet365",
    "BW": "betway",
    "IW": "interwetten",
    "BF": "betfair",
    "PS": "pinnacle",
    "WH": "william_hill",
    "VC": "vcbet",
    "1XB": "1xbet",
    "BFE": "betfair_exchange",
    "Max": MARKET_MAX,
    "Avg": MARKET_AVG,
}
BOOKMAKERS_OU_AH = {
    "B365": "bet365",
    "P": "pinnacle",
    "BFE": "betfair_exchange",
    "Max": MARKET_MAX,
    "Avg": MARKET_AVG,
}

# suffix -> selection
SELECTIONS_1X2 = {"H": "home", "D": "draw", "A": "away"}
SELECTIONS_OU = {">2.5": "over", "<2.5": "under"}
SELECTIONS_AH = {"AHH": "home", "AHA": "away"}

OU_LINE = 2.5
AH_OPENING_LINE_COLUMN = "AHh"
AH_CLOSING_LINE_COLUMN = "AHCh"
LEGACY_AH_LINE_COLUMN = "BbAHh"


@dataclass(frozen=True)
class OddsColumn:
    bookmaker: str
    market: str  # "1x2", "ou" or "ah"
    selection: str
    is_closing: bool
    line: float | None = None  # fixed line (over/under 2.5)
    line_column: str | None = None  # CSV column holding the line (asian handicap)


def _build_mapping() -> dict[str, OddsColumn]:
    mapping: dict[str, OddsColumn] = {}

    for prefix, bookmaker in BOOKMAKERS_1X2.items():
        for suffix, selection in SELECTIONS_1X2.items():
            mapping[f"{prefix}{suffix}"] = OddsColumn(bookmaker, "1x2", selection, False)
            mapping[f"{prefix}C{suffix}"] = OddsColumn(bookmaker, "1x2", selection, True)

    for prefix, bookmaker in BOOKMAKERS_OU_AH.items():
        for suffix, selection in SELECTIONS_OU.items():
            mapping[f"{prefix}{suffix}"] = OddsColumn(
                bookmaker, "ou", selection, False, line=OU_LINE
            )
            closing_col = f"{prefix}C{suffix}"
            mapping[closing_col] = OddsColumn(bookmaker, "ou", selection, True, line=OU_LINE)
        for suffix, selection in SELECTIONS_AH.items():
            mapping[f"{prefix}{suffix}"] = OddsColumn(
                bookmaker, "ah", selection, False, line_column=AH_OPENING_LINE_COLUMN
            )
            # Closing handicap columns put the C before AH: B365CAHH, not B365AHCH.
            closing_col = f"{prefix}C{suffix}"
            mapping[closing_col] = OddsColumn(
                bookmaker, "ah", selection, True, line_column=AH_CLOSING_LINE_COLUMN
            )

    mapping.update(_legacy_mapping())
    return mapping


def _legacy_mapping() -> dict[str, OddsColumn]:
    """BbMx*/BbAv* columns of the 2018-19 files (all opening odds)."""
    legacy: dict[str, OddsColumn] = {}
    for prefix, bookmaker in (("BbMx", MARKET_MAX), ("BbAv", MARKET_AVG)):
        for suffix, selection in SELECTIONS_1X2.items():
            legacy[f"{prefix}{suffix}"] = OddsColumn(bookmaker, "1x2", selection, False)
        for suffix, selection in SELECTIONS_OU.items():
            legacy[f"{prefix}{suffix}"] = OddsColumn(
                bookmaker, "ou", selection, False, line=OU_LINE
            )
        for suffix, selection in SELECTIONS_AH.items():
            legacy[f"{prefix}{suffix}"] = OddsColumn(
                bookmaker, "ah", selection, False, line_column=LEGACY_AH_LINE_COLUMN
            )
    return legacy


ODDS_COLUMNS: dict[str, OddsColumn] = _build_mapping()
