from vba.data.odds_mapping import ODDS_COLUMNS, OddsColumn, unmapped_odds_columns

# Odds columns copied from the real headers of three seasons (everything after AR,
# without the count columns Bb1X2/BbOU/BbAH and the line columns AHh/AHCh/BbAHh).
COLUMNS_1819 = (
    "B365H,B365D,B365A,BWH,BWD,BWA,IWH,IWD,IWA,PSH,PSD,PSA,WHH,WHD,WHA,VCH,VCD,VCA,"
    "BbMxH,BbAvH,BbMxD,BbAvD,BbMxA,BbAvA,BbMx>2.5,BbAv>2.5,BbMx<2.5,BbAv<2.5,"
    "BbMxAHH,BbAvAHH,BbMxAHA,BbAvAHA,PSCH,PSCD,PSCA"
)
COLUMNS_1920 = (
    "B365H,B365D,B365A,BWH,BWD,BWA,IWH,IWD,IWA,PSH,PSD,PSA,WHH,WHD,WHA,VCH,VCD,VCA,"
    "MaxH,MaxD,MaxA,AvgH,AvgD,AvgA,B365>2.5,B365<2.5,P>2.5,P<2.5,Max>2.5,Max<2.5,"
    "Avg>2.5,Avg<2.5,B365AHH,B365AHA,PAHH,PAHA,MaxAHH,MaxAHA,AvgAHH,AvgAHA,"
    "B365CH,B365CD,B365CA,BWCH,BWCD,BWCA,IWCH,IWCD,IWCA,PSCH,PSCD,PSCA,WHCH,WHCD,WHCA,"
    "VCCH,VCCD,VCCA,MaxCH,MaxCD,MaxCA,AvgCH,AvgCD,AvgCA,B365C>2.5,B365C<2.5,PC>2.5,"
    "PC<2.5,MaxC>2.5,MaxC<2.5,AvgC>2.5,AvgC<2.5,B365CAHH,B365CAHA,PCAHH,PCAHA,"
    "MaxCAHH,MaxCAHA,AvgCAHH,AvgCAHA"
)
COLUMNS_2425 = (
    "B365H,B365D,B365A,BWH,BWD,BWA,BFH,BFD,BFA,PSH,PSD,PSA,WHH,WHD,WHA,1XBH,1XBD,1XBA,"
    "MaxH,MaxD,MaxA,AvgH,AvgD,AvgA,BFEH,BFED,BFEA,B365>2.5,B365<2.5,P>2.5,P<2.5,"
    "Max>2.5,Max<2.5,Avg>2.5,Avg<2.5,BFE>2.5,BFE<2.5,B365AHH,B365AHA,PAHH,PAHA,"
    "MaxAHH,MaxAHA,AvgAHH,AvgAHA,BFEAHH,BFEAHA,B365CH,B365CD,B365CA,BWCH,BWCD,BWCA,"
    "BFCH,BFCD,BFCA,PSCH,PSCD,PSCA,WHCH,WHCD,WHCA,1XBCH,1XBCD,1XBCA,MaxCH,MaxCD,MaxCA,"
    "AvgCH,AvgCD,AvgCA,BFECH,BFECD,BFECA,B365C>2.5,B365C<2.5,PC>2.5,PC<2.5,MaxC>2.5,"
    "MaxC<2.5,AvgC>2.5,AvgC<2.5,BFEC>2.5,BFEC<2.5,B365CAHH,B365CAHA,PCAHH,PCAHA,"
    "MaxCAHH,MaxCAHA,AvgCAHH,AvgCAHA,BFECAHH,BFECAHA"
)


def test_every_real_odds_column_is_mapped():
    for columns in (COLUMNS_1819, COLUMNS_1920, COLUMNS_2425):
        unmapped = [c for c in columns.split(",") if c not in ODDS_COLUMNS]
        assert unmapped == []


def test_1x2_opening_and_closing():
    assert ODDS_COLUMNS["PSH"] == OddsColumn("pinnacle", "1x2", "home", False)
    assert ODDS_COLUMNS["PSCD"] == OddsColumn("pinnacle", "1x2", "draw", True)
    assert ODDS_COLUMNS["MaxA"] == OddsColumn("market_max", "1x2", "away", False)
    assert ODDS_COLUMNS["AvgCH"] == OddsColumn("market_avg", "1x2", "home", True)


def test_over_under_has_fixed_line():
    assert ODDS_COLUMNS["B365>2.5"] == OddsColumn("bet365", "ou", "over", False, line=2.5)
    assert ODDS_COLUMNS["PC<2.5"] == OddsColumn("pinnacle", "ou", "under", True, line=2.5)


def test_asian_handicap_reads_line_from_column():
    assert ODDS_COLUMNS["PAHH"].line_column == "AHh"
    assert ODDS_COLUMNS["PCAHA"] == OddsColumn("pinnacle", "ah", "away", True, line_column="AHCh")


def test_legacy_columns_map_to_betbrain_aggregates():
    # Betbrain max/avg are a different set of bookmakers than the Max*/Avg* market columns.
    assert ODDS_COLUMNS["BbMxH"] == OddsColumn("betbrain_max", "1x2", "home", False)
    assert ODDS_COLUMNS["BbAv<2.5"] == OddsColumn("betbrain_avg", "ou", "under", False, line=2.5)
    assert ODDS_COLUMNS["BbAvAHA"].line_column == "BbAHh"


def test_prefixes_follow_notes_txt():
    assert ODDS_COLUMNS["BWH"].bookmaker == "bet_and_win"  # Bet&Win, not Betway
    assert ODDS_COLUMNS["BFDD"].bookmaker == "betfred"
    assert ODDS_COLUMNS["BFD"].bookmaker == "betfair"  # draw odds, not Betfred
    assert ODDS_COLUMNS["BMGMA"].bookmaker == "betmgm"
    assert ODDS_COLUMNS["PH"].bookmaker == "pinnacle"  # alias of PSH
    assert ODDS_COLUMNS["LBA"].bookmaker == "ladbrokes"
    assert ODDS_COLUMNS["GB>2.5"].bookmaker == "gamebookers"


def test_skb_columns_map_to_skybet():
    # Columns reported as unmapped in the 2026-27 files.
    assert ODDS_COLUMNS["SKBH"] == OddsColumn("skybet", "1x2", "home", False)
    assert ODDS_COLUMNS["SKBCD"] == OddsColumn("skybet", "1x2", "draw", True)
    assert unmapped_odds_columns(["SKBH", "SKBD", "SKBA", "SKBCH", "SKBCD", "SKBCA"]) == []


def test_old_handicap_columns_use_their_own_line_column():
    assert ODDS_COLUMNS["GBAHH"].line_column == "GBAH"
    assert ODDS_COLUMNS["LBAHA"].line_column == "LBAH"


def test_unmapped_odds_columns_flags_only_odds_like_columns():
    header = ["Div", "Date", "FTR", "HS", "AHh", "BbAH", "PSH", "XYZH", "NEW>2.5", "Referee"]

    assert unmapped_odds_columns(header) == ["XYZH", "NEW>2.5"]


def test_real_headers_have_no_unmapped_odds_columns():
    for columns in (COLUMNS_1819, COLUMNS_1920, COLUMNS_2425):
        assert unmapped_odds_columns(columns.split(",")) == []


def test_non_odds_columns_are_not_mapped():
    for column in ("Div", "Date", "FTHG", "AHh", "Bb1X2", "Referee"):
        assert column not in ODDS_COLUMNS
