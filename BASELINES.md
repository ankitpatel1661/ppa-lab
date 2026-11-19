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

| Baseline | Date | Commit | Code | Method | Forward EUR/MWh | Forward date | Scen. | Solar 10 yr | Wind 10 yr | Solar 2027 | Wind 2027 | Test files |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `v0.1.0` | 2026-10-07 | `31206ee` | 0.1.0 | — | — | — | — | — | — | — | — | 9 |
| `v0.2.0` | 2026-10-08 | `a749eab` | 0.2.0 | — | — | — | — | — | — | — | — | 12 |
| `v0.3.0` | 2026-10-13 | `f9c387b` | 0.3.0 | 0 | — | — | — | — | — | — | — | 15 |
| `v0.4.0` | 2026-10-13 | `e2a5c41` | 0.4.0 | 0.1 | — | — | — | — | — | — | — | 21 |
| `v0.5.0` | 2026-10-13 | `75c8521` | 0.5.0 | 0.2 | 85.00 | *assumed* | — | — | — | — | — | 24 |
| `v0.6.0` | 2026-10-14 | `168043b` | 0.6.0 | 0.3 | 85.00 | *assumed* | — | — | — | — | — | 28 |
| `v0.7.0` | 2026-10-14 | `af91a78` | 0.7.0 | 0.4 | 85.00 | *assumed* | — | — | — | — | — | 30 |
| `v0.9.0` | 2026-10-14 | `e636b73` | 0.9.0 | 0.4 | 85.00 | *assumed* | 496 | 33.3 | 68.4 | 33.3 | 68.4 | 33 |
| `v1.0.0` | 2026-10-14 | `ea366d0` | 1.0.0 | 1.0 | 85.00 | *assumed* | 496 | 33.3 | 68.4 | 33.3 | 68.4 | 35 |
| `v1.1.0` | 2026-10-15 | `e43b8da` | 1.1.0 | 1.1 | 140.21 | 2026-10-09 | 496 | 50.6 | 80.1 | 78.6 | 120.5 | 36 |
| `v1.2.0` | 2026-10-15 | `37b7980` | 1.2.0 | 1.2 | 140.21 | 2026-10-09 | 496 | 45.2 | 81.8 | 76.0 | 123.0 | 36 |
| `v1.3.0` | 2026-10-15 | `f3251c5` | 1.3.0 | 1.3 | 140.21 | 2026-10-09 | 496 | 44.7 | 80.0 | 75.2 | 120.8 | 36 |
| `v1.4.0` | 2026-10-15 | `59f1a73` | 1.4.0 | 1.3 | 140.21 | 2026-10-09 | 496 | 44.7 | 80.0 | 75.2 | 120.8 | 36 |
| `v1.5.0` | 2026-10-15 | `de78522` | 1.5.0 | 1.5 | 140.21 | 2026-10-09 | 496 | 34.9 | 77.3 | 75.2 | 120.8 | 37 |
| `v1.6.0` | 2026-10-15 | `651575f` | 1.6.0 | 1.6 | 140.21 | 2026-10-09 | 496 | 36.8 | 77.5 | 74.6 | 120.7 | 37 |
| `v1.7.0` | 2026-10-15 | `e1b7a89` | 1.7.0 | 1.7 | 140.21 | 2026-10-09 | 496 | 28.1 | 78.1 | 64.5 | 121.4 | 37 |
| `v1.8.0` | 2026-10-15 | `92ce664` | 1.8.0 | 1.8 | 140.21 | 2026-10-09 | 496 | 28.1 | 78.1 | 64.5 | 121.4 | 37 |
| `v1.9.0` | 2026-10-16 | `871aebe` | 1.9.0 | 1.9 | 140.21 | 2026-10-09 | 496 | 28.1 | 78.1 | 64.5 | 121.4 | 38 |
| `v1.10.0` | 2026-10-16 | `4481840` | 1.10.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 27.4 | 78.6 | 63.8 | 121.9 | 41 |
| `v1.11.0` | 2026-10-16 | `343def2` | 1.11.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 21.4 | 78.6 | 63.8 | 121.9 | 42 |
| `v1.11.1` | 2026-10-22 | `ac208a1` | 1.11.1 | 1.10 | 140.21 | 2026-10-09 | 496 | 21.4 | 78.6 | 63.8 | 121.9 | 42 |
| `v1.12.0` | 2026-10-23 | `e3bb8ce` | 1.12.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 21.4 | 78.6 | 63.8 | 121.9 | 42 |
| `v1.13.0` | 2026-10-23 | `44b0307` | 1.13.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 21.4 | 78.6 | 63.8 | 121.9 | 43 |
| `v1.14.0` | 2026-10-26 | `010de07` | 1.14.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 21.4 | 78.6 | 63.8 | 121.9 | 43 |
| `v1.15.0` | 2026-10-26 | `5bad5a8` | 1.15.0 | 1.10 | 140.21 | 2026-10-09 | 496 | 21.4 | 78.6 | 63.8 | 121.9 | 43 |
| `v1.15.1` | 2026-11-03 | `7144b9e` | 1.15.1 | 1.11 | 140.21 | 2026-10-09 | 496 | 21.4 | 78.6 | 63.8 | 121.9 | 43 |
| `v1.16.0` | 2026-11-04 | `62f4317` | 1.16.0 | 1.11 | **154.42** | **2026-10-23** | 496 | **22.6** | **81.5** | **73.2** | **135.5** | 43 |

**Columns.** *Code* is `version` in `pyproject.toml`. *Method* is the version
line in `METHODOLOGY.md`. *Forward* and *Forward date* are `forward_eur_mwh` and
`forward_date` in `config/project.toml`. *Scen.* is the joint weather–price
scenario count. *Solar 10 yr* and *Wind 10 yr* are the ten-year indicative
pay-as-produced prices in EUR/MWh from `reports/results.json`
(`parks.<park>.tenor.indicative`): the headline numbers each baseline published in
the README, the memo and the dashboard. *Solar 2027* and *Wind 2027* are the
first-year indicative prices (`parks.<park>.stack_eur_mwh.indicative`), the price
stack of the delivery year alone. Until `v1.1.0` there was one flat assumed
forward and no capture-rate trend, so the two coincide; from `v1.1.0` the forward
curve falls after 2027 and they part. *Test files* is the count of
`tests/test_*.py`.

Em-dashes are absences, not failures: `METHODOLOGY.md` begins at `v0.3.0`, a
forward assumption at `v0.5.0` (Step 5 is the price model), and published
results at `v0.9.0`, which is Step 9 — the memo and dashboard. Nothing was
published before there was something to publish.

---

## 2. What the register shows

### 2.1 The methodology version lags the code version: mostly by design, once by mistake

Nine baselines carry a method version older than their code:

| Baselines | Code | Method on record | Method in force | Why |
|---|---|---|---|---|
| `v1.4.0` | 1.4.0 | 1.3 | 1.3 | history extended to 2021; the method did not change |
| `v1.11.0` | 1.11.0 | 1.10 | 1.11 | **lag by mistake:** the build-out scenarios changed the method (`METHODOLOGY.md`'s own changelog has its v1.11 entry at this tag), but the version line was not bumped |
| `v1.11.1` – `v1.15.0` | 1.11.1 – 1.15.0 | 1.10 | 1.11 | the same stale line, carried through a documentation fix and four dashboard releases that did not change the method |
| `v1.15.1` | 1.15.1 | 1.11 | 1.11 | version line corrected (commit `2546fc5`); dashboard fixes only |
| `v1.16.0` | 1.16.0 | 1.11 | 1.11 | forward re-anchored to newer quotes; the method did not change |

*Method on record* is the version line as committed, which is what the register's
*Method* column shows; *method in force* is what the methodology's own changelog
says applied.

The design holds for `v1.4.0`, `v1.15.1` and `v1.16.0`. A release that extends the
data, fixes the dashboard or re-anchors the forward changes code and numbers
without changing the method, so `METHODOLOGY.md` stays put, and "has the method
changed since I last read it?" is answerable by comparing one number.

The six baselines `v1.11.0` – `v1.15.0` are the exception: they under-report the
method by one version, and the comparison gives the wrong answer for them. The
register's price columns show what the version line missed: the ten-year solar
price fell 27.4 → 21.4 at `v1.11.0`.

Nothing analytical moved from `v1.12.0` through `v1.15.0`: four releases, the
dashboard gaining explanations and then Italian and Spanish, and the published
prices (21.4 and 78.6 over ten years) identical throughout.

### 2.2 Re-anchoring to the market is visible and attributable

The forward moved three times. The ten-year price, the headline the README, the
memo and the dashboard publish, moved with it, and between the moves the model
changed:

| | Forward | Solar 10 yr | Wind 10 yr | Solar 2027 |
|---|---|---|---|---|
| `v0.9.0` – `v1.0.0` | 85.00 *assumed* | 33.3 | 68.4 | 33.3 |
| `v1.1.0` – `v1.15.1` | 140.21 (9 Oct 2026) | 50.6 → 21.4 | 80.1 → 78.6 | 78.6 → 63.8 |
| `v1.16.0` | 154.42 (23 Oct 2026) | 22.6 | 81.5 | 73.2 |

Two things are separable here that would otherwise be confounded. At `v1.1.0` the
solar ten-year price rises 33.3 → 50.6 purely because the price level stopped
being an assumption and became the market's. It then falls to 21.4 across
`v1.2.0` – `v1.11.0` with the forward held constant. That decline is modelling
work, not market movement:

| Baseline | What changed | Solar 10 yr |
|---|---|---|
| `v1.2.0` | the market's quarterly shape; a solar capture-rate trend of −1 pp a year | −5.4 |
| `v1.3.0` | the two real parks, calibrated to their published yields | −0.5 |
| `v1.5.0` | the capture rate's response to the price level | −9.8 |
| `v1.6.0` | the out-of-sample test and the negative-price tail | +1.9 |
| `v1.7.0` | the build-out trend of the intraday shape | −8.7 |
| `v1.10.0` | the balancing cost, measured instead of assumed | −0.7 |
| `v1.11.0` | solar and storage build-out scenarios after 2027 | −6.0 |

The largest steps are the capture rate's response to the level (`v1.5.0`) and the
build-out trend (`v1.7.0`). Only at `v1.16.0` does the price rise again, to 22.6,
on a 10% higher Cal-27 forward: by 1.2 only, because Cal-29, which prices
2029–2036, barely moved.

The first-year price is kept as a second column, but it cannot stand in for the
ten-year one. A change that acts only on later years, like the build-out scenarios
at `v1.11.0`, leaves it unchanged (63.8 before and after). Until revision 1.1 this
register showed only the first-year price and so missed that change.

Without the register those effects are one number drifting. With it, each is
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
   — and the register shows four numbers per release. It is an index to the
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
| 1.1 | 2026-11-19 | Ten-year indicative prices added: the headline each baseline published. The register showed only the first-year price, labelled as that headline, which hid the `v1.11.0` change (27.4 → 21.4). §2.1 corrected: the method line of `v1.11.0` – `v1.15.0` lagged by mistake, not by design. §2.2 restated in the published prices. |
