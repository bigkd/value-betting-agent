"""Single place that maps football-data.co.uk odds columns to the long `odds` format.

Each CSV column resolves to (bookmaker, market, selection, is_closing) plus the
line of the bet. To support a new bookmaker or market, add it to the tables below;
nothing else in the ingestion needs to change. Prefixes are documented in
https://www.football-data.co.uk/notes.txt

Column naming in the CSVs:

- 1X2 opening:        {prefix}H / {prefix}D / {prefix}A          e.g. B365H, PSD, AvgA
- 1X2 closing:        {prefix}CH / {prefix}CD / {prefix}CA       e.g. PSCH, MaxCD
- Over/under opening: {prefix}>2.5 / {prefix}<2.5                e.g. B365>2.5, P<2.5
- Over/under closing: {prefix}C>2.5 / {prefix}C<2.5              e.g. PC>2.5
- Asian handicap:     {prefix}AHH / {prefix}AHA (opening, line in column AHh)
                      {prefix}CAHH / {prefix}CAHA (closing, line in column AHCh)

Prefixes are not consistent between markets (Pinnacle is PS or P in 1X2 but P in
over/under and handicap), hence one table per market family.

The handicap `line` is stored exactly as in the CSV, which is the handicap of the
home team, for both the home and the away selection.

Aggregates: Max*/Avg* are the market-wide maximum/average (market_max/market_avg).
The Bb* columns of the old files (up to 2018-19) are the maximum/average of the
Betbrain bookmakers, a different set, so they map to betbrain_max/betbrain_avg.
Closing odds in 2018-19 exist only for Pinnacle 1X2 (PSC*).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

# Pseudo-bookmakers for the aggregates football-data computes.
MARKET_MAX = "market_max"
MARKET_AVG = "market_avg"
BETBRAIN_MAX = "betbrain_max"
BETBRAIN_AVG = "betbrain_avg"

# prefix -> bookmaker, per market family.
BOOKMAKERS_1X2 = {
    "1XB": "1xbet",
    "B365": "bet365",
    "BF": "betfair",
    "BFD": "betfred",
    "BFE": "betfair_exchange",
    "BMGM": "betmgm",
    "BS": "blue_square",
    "BV": "betvictor",
    "BW": "bet_and_win",
    "CL": "coral",
    "GB": "gamebookers",
    "IW": "interwetten",
    "LB": "ladbrokes",
    "P": "pinnacle",  # alias of PS used in some files (PH/PD/PA)
    "PP": "paddy_power",
    "PS": "pinnacle",
    "SB": "sportingbet",
    "SJ": "stan_james",
    "SK": "skybet",
    "SO": "sporting_odds",
    "SY": "stanleybet",
    "VC": "vc_bet",  # now BetVictor, but the notes list it separately from BV
    "WH": "william_hill",
    "Max": MARKET_MAX,
    "Avg": MARKET_AVG,
}
BOOKMAKERS_OU = {
    "B365": "bet365",
    "BFE": "betfair_exchange",
    "GB": "gamebookers",
    "P": "pinnacle",
    "Max": MARKET_MAX,
    "Avg": MARKET_AVG,
}
BOOKMAKERS_AH = {
    "B365": "bet365",
    "BFE": "betfair_exchange",
    "GB": "gamebookers",
    "LB": "ladbrokes",
    "P": "pinnacle",
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
# Old files give these bookmakers their own handicap column (opening odds only).
AH_OWN_LINE_COLUMNS = {"GB": "GBAH", "LB": "LBAH"}


@dataclass(frozen=True)
class OddsColumn:
    bookmaker: str
    market: str  # "1x2", "ou" or "ah"
    selection: str
    is_closing: bool
    line: float | None = None  # fixed line (over/under 2.5)
    line_column: str | None = None  # CSV column holding the line (asian handicap)


def _add(mapping: dict[str, OddsColumn], column: str, spec: OddsColumn) -> None:
    if column in mapping:
        raise ValueError(f"Odds column {column!r} is mapped twice: check the prefix tables")
    mapping[column] = spec


def _build_mapping() -> dict[str, OddsColumn]:
    mapping: dict[str, OddsColumn] = {}

    for prefix, bookmaker in BOOKMAKERS_1X2.items():
        for suffix, selection in SELECTIONS_1X2.items():
            _add(mapping, f"{prefix}{suffix}", OddsColumn(bookmaker, "1x2", selection, False))
            _add(mapping, f"{prefix}C{suffix}", OddsColumn(bookmaker, "1x2", selection, True))

    for prefix, bookmaker in BOOKMAKERS_OU.items():
        for suffix, selection in SELECTIONS_OU.items():
            spec = OddsColumn(bookmaker, "ou", selection, False, line=OU_LINE)
            _add(mapping, f"{prefix}{suffix}", spec)
            closing = OddsColumn(bookmaker, "ou", selection, True, line=OU_LINE)
            _add(mapping, f"{prefix}C{suffix}", closing)

    for prefix, bookmaker in BOOKMAKERS_AH.items():
        opening_line = AH_OWN_LINE_COLUMNS.get(prefix, AH_OPENING_LINE_COLUMN)
        for suffix, selection in SELECTIONS_AH.items():
            opening = OddsColumn(bookmaker, "ah", selection, False, line_column=opening_line)
            _add(mapping, f"{prefix}{suffix}", opening)
            if prefix in AH_OWN_LINE_COLUMNS:
                continue  # those old files have no closing handicap odds
            # Closing handicap columns put the C before AH: B365CAHH, not B365AHCH.
            closing = OddsColumn(
                bookmaker, "ah", selection, True, line_column=AH_CLOSING_LINE_COLUMN
            )
            _add(mapping, f"{prefix}C{suffix}", closing)

    for prefix, bookmaker in (("BbMx", BETBRAIN_MAX), ("BbAv", BETBRAIN_AVG)):
        for suffix, selection in SELECTIONS_1X2.items():
            _add(mapping, f"{prefix}{suffix}", OddsColumn(bookmaker, "1x2", selection, False))
        for suffix, selection in SELECTIONS_OU.items():
            spec = OddsColumn(bookmaker, "ou", selection, False, line=OU_LINE)
            _add(mapping, f"{prefix}{suffix}", spec)
        for suffix, selection in SELECTIONS_AH.items():
            spec = OddsColumn(bookmaker, "ah", selection, False, line_column=LEGACY_AH_LINE_COLUMN)
            _add(mapping, f"{prefix}{suffix}", spec)

    return mapping


ODDS_COLUMNS: dict[str, OddsColumn] = _build_mapping()

# Columns that are not odds even though some of them end like an odds column.
# Used to avoid false alarms when looking for unmapped odds.
KNOWN_NON_ODDS_COLUMNS = frozenset(
    {
        "Div", "Date", "Time", "HomeTeam", "AwayTeam", "Referee", "Attendance",
        "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR",
        "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR",
        # Number-of-bookmakers columns and handicap line columns.
        "Bb1X2", "BbOU", "BbAH", "BbAHh", "AHh", "AHCh", "B365AH", "GBAH", "LBAH",
    }
)  # fmt: skip

# Odds-looking endings: 1X2 (H/D/A), over/under 2.5 and asian handicap (AHH/AHA).
_ODDS_LIKE = re.compile(r"([HDA]|[<>]2\.5|AH[HA])$")


def unmapped_odds_columns(header: Iterable[str]) -> list[str]:
    """Columns that look like odds but are not in ODDS_COLUMNS (data we would lose)."""
    return [
        column
        for column in header
        if column not in ODDS_COLUMNS
        and column not in KNOWN_NON_ODDS_COLUMNS
        and _ODDS_LIKE.search(column)
    ]
