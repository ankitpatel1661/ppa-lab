# Test fixtures

Real responses from the Energy-Charts API, saved on 7 October 2026. They are small
on purpose and contain the difficult cases the code must handle.

| File | Why it is here |
|---|---|
| `price_DE-LU_2025-09-30_2025-10-01.json` | Hourly prices on 30 Sep, quarter-hourly from 1 Oct 2025 (15-minute MTU go-live) |
| `price_DE-LU_2025-03-30.json` | Spring daylight-saving day: only 23 hourly prices |
| `price_DE-LU_2025-10-26.json` | Autumn daylight-saving day: 100 quarter-hours (25 hours) |
| `public_power_de_2025-03-30.json` | Generation by technology on the spring DST day (92 quarter-hours) |

Licence: CC BY 4.0, Bundesnetzagentur | SMARD.de, via Energy-Charts (Fraunhofer ISE).
