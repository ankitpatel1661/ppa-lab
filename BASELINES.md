# Baseline Record

What each released baseline was made of, and what it produced.

This is the configuration status accounting register for
[CONFIGURATION_MANAGEMENT.md](CONFIGURATION_MANAGEMENT.md) §4. It answers the
question a reader of any published number needs answered: **which code, which
method, which market inputs produced it.**

Every value below was read out of the repository at its tag, not transcribed
from the changelog. The three integrity checks in §3 were run against all 27
baselines and all pass.

---

## 1. The register

| Baseline | Date | Commit | Code | Method | Forward EUR/MWh | Forward date | Scen. | Solar ind. | Wind ind. | Test files |
|---|---|---|---|---|---|---|---|---|---|---|
| `v0.1.0` | 2026-10-07 | `31206ee` | 0.1.0 | — | — | — | — | — | — | 9 |
| `v0.2.0` | 2026-10-08 | `a749eab` | 0.2.0 | — | — | — | — | — | — | 12 |
| `v0.3.0` | 2026-10-13 | `f9c387b` | 0.3.0 | 0 | — | — | — | — | — | 15 |
| `v0.4.0` | 2026-10-13 | `e2a5c41` | 0.4.0 | 0.1 | — | — | — | — | — | 21 |
| `v0.5.0` | 2026-10-13 | `75c8521` | 0.5.0 | 0.2 | 85.00 | *assumed* | — | — | — | 24 |
| `v0.6.0` | 2026-10-14 | `168043b` | 0.6.0 | 0.3 | 85.00 | *assumed* | — | — | — | 28 |
| `v0.7.0` | 2026-10-14 | `af91a78` | 0.7.0 | 0.4 | 85.00 | *assumed* | — | — | — | 30 |
| `v0.9.0` | 2026-10-14 | `e636b73` | 0.9.0 | 0.4 | 85.00 | *assumed* | 496 | 33.3 | 68.4 | 33 |
| `v1.0.0` | 2026-10-14 | `ea366d0` | 1.0.0 | 1.0 | 85.00 | *assumed* | 496 | 33.3 | 68.4 | 35 |
| `v1.1.0` | 2026-10-15 | `e43b8da` | 1.1.0 | 1.1 | 140.21 | 2026-10-09 | 496 | 78.6 | 120.5 | 36 |
| `v1.2.0` | 2026-10-15 | `37b7980` | 1.2.0 | 1.2 | 140.21 | 2026-10-09 | 496 | 76.0 | 123.0 | 36 |
| `v1.3.0` | 2026-10-15 | `f3251c5` | 1.3.0 | 1.3 | 140.21 | 2026-10-09 | 496 | 75.2 | 120.8 | 36 |
| `v1.4.0` | 2026-10-15 | `59f1a73` | 1.4.0 | 1.3 | 140.21 | 2026-10-09 | 496 | 75.2 | 120.8 | 36 |
| `v1.5.0` | 2026-10-15 | `de78522` | 1.5.0 | 1.5 | 140.21 | 2026-10-09 | 496 | 75.2 | 120.8 | 37 |
| `v1.6.0` | 2026-10-15 | `651575f` | 1.6.0 | 1.6 | 140.21 | 2026-10-09 | 496 | 74.6 | 120.7 | 37 |
| `v1.7.0` | 2026-10-15 | `e1b7a89` | 1.7.0 | 1.7 | 140.21 | 2026-10-09 | 496 | 64.5 | 121.4 | 37 |
| `v1.8.0` | 2026-10-15 | `92ce664` | 1.8.0 | 1.8 | 140.21 | 2026-10-09 | 496 | 64.5 | 121.4 | 37 |
| `v1.9.0` | 2026-10-16 | `871aebe` | 1.9.0 | 1.9 | 140.21 | 2026-10-09 | 496 | 64.5 | 121.4 | 38 |
| `v1.10.0` | 2026-10-16 | `4481840` | 1.10.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 63.8 | 121.9 | 41 |
| `v1.11.0` | 2026-10-16 | `343def2` | 1.11.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 63.8 | 121.9 | 42 |
| `v1.11.1` | 2026-10-22 | `ac208a1` | 1.11.1 | 1.10 | 140.21 | 2026-10-09 | 496 | 63.8 | 121.9 | 42 |
| `v1.12.0` | 2026-10-23 | `e3bb8ce` | 1.12.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 63.8 | 121.9 | 42 |
| `v1.13.0` | 2026-10-23 | `44b0307` | 1.13.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 63.8 | 121.9 | 43 |
| `v1.14.0` | 2026-10-26 | `010de07` | 1.14.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 63.8 | 121.9 | 43 |
| `v1.15.0` | 2026-10-26 | `5bad5a8` | 1.15.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 63.8 | 121.9 | 43 |
| `v1.15.1` | 2026-11-03 | `7144b9e` | 1.15.1 | 1.11 | 140.21 | 2026-10-09 | 496 | 63.8 | 121.9 | 43 |
| `v1.16.0` | 2026-11-04 | `62f4317` | 1.16.0 | 1.11 | **154.42** | **2026-10-23** | 496 | **73.2** | **135.5** | 43 |

**Columns.** *Code* is `version` in `pyproject.toml`. *Method* is the version
line in `METHODOLOGY.md`. *Forward* and *Forward date* are `forward_eur_mwh` and
`forward_date` in `config/project.toml`. *Scen.* is the joint weather–price
scenario count. *Solar ind.* and *Wind ind.* are the indicative pay-as-produced
prices in EUR/MWh from `reports/results.json`
(`parks.<park>.stack_eur_mwh.indicative`), the headline numbers each baseline
published. *Test files* is the count of `tests/test_*.py`.

Em-dashes are absences, not failures: `METHODOLOGY.md` begins at `v0.3.0`, a
forward assumption at `v0.5.0` (Step 5 is the price model), and published
results at `v0.9.0`, which is Step 9 — the memo and dashboard. Nothing was
published before there was something to publish.

---

## 2. What the register shows

### 2.1 The methodology version lags the code version, deliberately

Eight baselines carry a method version older than their code:

| Baselines | Code | Method | Why |
|---|---|---|---|
| `v1.4.0` | 1.4.0 | 1.3 | history extended to 2021; no change to the method |
| `v1.11.0` – `v1.15.0` | 1.11.0 – 1.15.0 | 1.10 | build-out scenarios, then four dashboard releases |
| `v1.15.1` | 1.15.1 | 1.11 | — |

This is the design, not drift. A release that extends the data or rebuilds the
dashboard changes code and numbers without changing the method, so
`METHODOLOGY.md` stays put. It means "has the method changed since I last read
it?" is answerable by comparing one number.

The clearest case is `v1.12.0` through `v1.15.0`: four releases, the dashboard
gaining explanations and then Italian and Spanish, and the published prices
(63.8 and 121.9) identical throughout. Method 1.10 the whole way. The register
shows at a glance that nothing analytical moved.

### 2.2 Re-anchoring to the market is visible and attributable

The forward moved three times, and every published price moved with it:

| | Forward | Solar indicative | Wind indicative |
|---|---|---|---|
| `v0.9.0` – `v1.0.0` | 85.00 *assumed* | 33.3 | 68.4 |
| `v1.1.0` – `v1.15.1` | 140.21 (9 Oct 2026) | 78.6 → 63.8 | 120.5 → 121.9 |
| `v1.16.0` | 154.42 (23 Oct 2026) | 73.2 | 135.5 |

Two things are separable here that would otherwise be confounded. At `v1.1.0`
the solar indicative jumps 33.3 → 78.6 purely because the price level stopped
being an assumption and became the market's. It then falls to 63.8 across
`v1.2.0` – `v1.10.0` with the forward held constant — that decline is modelling
work, not market movement: the quarterly shape (`v1.2.0`), the real parks
(`v1.3.0`), the capture-rate response to the level (`v1.5.0`), the out-of-sample
correction (`v1.6.0`) and the build-out trend (`v1.7.0`, the single largest step
at 74.6 → 64.5). Only at `v1.16.0` does it rise again, to 73.2, on a 10% higher
forward.

Without the register those two effects are one number drifting. With it, each is
attributable to a release and a ticket.

### 2.3 The test suite grew with the model

9 test files at `v0.1.0`, 43 at `v1.16.0`. No baseline reduced the count.

---

## 3. Integrity checks

Run across all 27 baselines by reading each file at its tag:

| Check | Result |
|---|---|
| Tag name matches `version` in `pyproject.toml` | **27/27, no mismatch** |
| `ppa_lab_version` in `reports/results.json` matches `pyproject.toml` | **20/20, no mismatch** |
| `forward.price_eur_mwh` in `results.json` matches `forward_eur_mwh` in `config/project.toml` | **20/20, no mismatch** |

The second check is the valuable one. `results.json` records the code version
that generated it, so published results carry their own provenance: a report
cannot silently belong to a different baseline than the code beside it. Across
every baseline that published results, the two agree.

The third check confirms the same for market inputs — no baseline published a
price stack built on a forward other than the one its configuration states.

### Reproducing these checks

```bash
# tag vs pyproject
for t in $(git tag); do
  v=$(git show $t:pyproject.toml | sed -n 's/^version = "\(.*\)"/\1/p')
  [ "$t" = "v$v" ] || echo "MISMATCH $t -> $v"
done

# results.json provenance vs pyproject, and forward vs config
for t in $(git tag); do
  git cat-file -e $t:reports/results.json 2>/dev/null || continue
  rv=$(git show $t:reports/results.json | python3 -c 'import json,sys;print(json.load(sys.stdin)["ppa_lab_version"])')
  pv=$(git show $t:pyproject.toml | sed -n 's/^version = "\(.*\)"/\1/p')
  [ "$rv" = "$pv" ] || echo "PROVENANCE $t: results $rv vs code $pv"
done
```

---

## 4. Limitations

1. **The register is generated by hand and committed.** Nothing recomputes it on
   release. A new baseline will not appear here until someone adds it, and the
   integrity checks in §3 are run deliberately, not by CI. Adding them to the
   release step would close this; it is not closed today.

2. **The indicative prices are headline numbers, not the whole result.** Each
   baseline's `results.json` holds far more — premia, CFaR, structures, hedging
   — and the register shows two numbers per release. It is an index to the
   baselines, not a substitute for reading one.

3. **"Reproduces" is not asserted here.** The register records what each
   baseline *published*. It does not claim that checking out `v0.9.0` today and
   running `make all` reproduces 33.3 and 68.4, because raw data is not under
   version control and depends on upstream APIs — see
   `CONFIGURATION_MANAGEMENT.md` §6.3. The audit procedure in §5.4 of that
   document is how you would find out for a given baseline.

4. **Two baselines predate `METHODOLOGY.md`** (`v0.1.0`, `v0.2.0`) and seven
   predate published results. For those, "which method produced this" is
   answerable only from the code and the learning-track pages at that tag.

---

## 5. Revision history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-11-16 | First issue. 27 baselines, three integrity checks all passing. |
