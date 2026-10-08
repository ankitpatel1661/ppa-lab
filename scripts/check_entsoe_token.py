"""Check that your ENTSO-E token works, and reconcile ENTSO-E with Energy-Charts.

    .venv/bin/python scripts/check_entsoe_token.py              # default: 2025-10-01
    .venv/bin/python scripts/check_entsoe_token.py 2025-06-01

The token is read from ENTSOE_API_KEY or from .env, and is never printed.
Exit codes: 0 = OK, 1 = ENTSO-E request failed, 2 = no token configured.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

from ppa_lab.data.entsoe import EntsoeClient, EntsoeError, load_api_key

ROOT = Path(__file__).resolve().parents[1]
TZ = "Europe/Berlin"


def main(argv: list[str]) -> int:
    day = date.fromisoformat(argv[1]) if len(argv) > 1 else date(2025, 10, 1)

    key = load_api_key(ROOT / ".env")
    if not key:
        print("No token found. Copy .env.example to .env and set ENTSOE_API_KEY=...")
        return 2
    print(f"Token loaded ({len(key)} characters, not shown).")

    try:
        every = EntsoeClient(api_key=key).day_ahead_prices("DE-LU", day, day, TZ, sequence=None)
    except EntsoeError as exc:
        print(f"ENTSO-E check FAILED: {exc}")
        return 1
    entsoe = every[every["sequence"] == 1]  # SDAC auction (see ppa_lab.data.entsoe)
    resolutions = ", ".join(f"{int(r)} min" for r in sorted(entsoe["resolution_min"].unique()))
    sequences = ", ".join(str(int(s)) for s in sorted(every["sequence"].unique()))
    print(
        f"ENTSO-E OK: {len(entsoe)} SDAC price rows for {day} (resolution: {resolutions}); "
        f"auction sequences in the response: {sequences}."
    )

    native = ROOT / "data" / "processed" / "prices_native.parquet"
    if not native.exists():
        print("No Energy-Charts data to compare with; run `make all` first.")
        return 0
    ec = pd.read_parquet(native)
    ec_day = ec[ec.index.tz_convert(TZ).date == day]
    if ec_day.empty:
        print(f"Energy-Charts has no data for {day}; cross-check skipped.")
        return 0

    res = int(ec_day["interval_min"].mode().iloc[0])
    joined = pd.concat(
        {
            "entsoe": entsoe.loc[entsoe["resolution_min"] == res, "price_eur_mwh"],
            "energy_charts": ec_day["price_eur_mwh"],
        },
        axis=1,
    ).dropna()
    max_diff = float((joined["entsoe"] - joined["energy_charts"]).abs().max())
    print(
        f"Cross-check at {res}-minute resolution: {len(joined)} of {len(ec_day)} intervals "
        f"matched, largest difference {max_diff:.2f} EUR/MWh."
    )
    if len(joined) == len(ec_day) and max_diff < 0.01:
        print("RECONCILED: ENTSO-E and Energy-Charts agree.")
    else:
        print("DIFFERENCES FOUND: investigate before trusting either source.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
