"""Report team names in the database that have no alias.

Run with: uv run python -m vba.data.team_check
Exit code is 1 when there are unknown names, so it can be used in scripts.
"""

import sys
from pathlib import Path

from vba.data.db import DEFAULT_DB_PATH, connect, create_schema
from vba.data.teams import unknown_team_names


def check(db_path: Path | str = DEFAULT_DB_PATH) -> int:
    """Print the football-data names without alias; return the process exit code."""
    con = connect(db_path)
    try:
        # The database may predate the team tables, so make sure they exist first.
        create_schema(con)
        unknown = unknown_team_names(con)
    finally:
        con.close()
    if unknown:
        print(f"{len(unknown)} team names have no alias:")
        for name in unknown:
            print(f"  {name}")
        return 1
    print("All team names have an alias.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
