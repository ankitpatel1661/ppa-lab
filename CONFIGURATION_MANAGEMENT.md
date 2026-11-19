# Configuration Management Plan

How this project identifies what it is made of, controls changes to it, records
what changed, and verifies that a given version still produces the numbers it
claims.

This plan is organised around the five configuration-management functions that
[SAE EIA-649](https://www.sae.org/standards/content/eia649c/) and
[ISO 10007](https://www.iso.org/standard/70400.html) define:

| # | Function | Where it lives |
|---|---|---|
| 1 | Configuration management planning | this document |
| 2 | Configuration identification | [§2](#2-configuration-identification) — the item register and version schemes |
| 3 | Configuration change management | [§3](#3-configuration-change-management) — tickets, branches, CI, release |
| 4 | Configuration status accounting | [§4](#4-configuration-status-accounting) — CHANGELOG and tagged baselines |
| 5 | Configuration verification and audit | [§5](#5-configuration-verification-and-audit) — tests, DQ checks, reconciliation |

Read [§6](#6-limitations) before relying on any of it. This is a single-maintainer
project and the plan says plainly where that weakens the controls.

---

## 1. Scope and purpose

`ppa-lab` prices and measures the risk of renewable power purchase agreements for
two German parks, using public market and weather data. Its outputs are numbers
that someone might act on — a fair price, a capture rate, a cash-flow-at-risk —
so the project has to be able to answer three questions at any time:

1. **What exactly produced this number?** Which code, which assumptions, which
   methodology, which input data.
2. **What changed since the last time, and why?**
3. **Is it still correct?** Does the version still reconcile against officially
   published market values.

Configuration management is how those questions stay answerable. The scope is the
whole repository: code, assumptions, data, methodology, reports and the
dashboard.

---

## 2. Configuration identification

### 2.1 Configuration item register

| ID | Configuration item | Path | Controlled by | Rebuildable? |
|---|---|---|---|---|
| CI-01 | Source code (57 modules) | `src/ppa_lab/` | git + `pyproject.toml` version | — |
| CI-02 | Assumption and parameter set (63 sections) | `config/project.toml` | git, in-file comments | — |
| CI-03 | Methodology document | `METHODOLOGY.md` | **its own version line** (see §2.3) | — |
| CI-04 | Verification tolerances (29 entries) | `[[reconciliation]]` in `config/project.toml` | git | — |
| CI-05 | Test suite (43 modules + `conftest.py`, 310 tests) and offline fixtures | `tests/`, `tests/fixtures/` | git | — |
| CI-06 | Committed reference data | `data/reference/` | git | no — published source |
| CI-07 | Raw data cache | `data/raw/` | **not tracked** (gitignored) | yes — `make data` |
| CI-08 | Processed datasets | `data/processed/` | **not tracked** (gitignored) | yes — `make build` |
| CI-09 | Step reports and results (10 reports + `results.json`) | `reports/` | git | yes — `make all` |
| CI-10 | Report figures (26 files) | `reports/figures/` | git | yes — `make all` |
| CI-11 | Architecture decision records | `docs/decisions/` | git, sequential ADR numbers | — |
| CI-12 | Change requests and acceptance criteria (21 tickets) | `docs/BACKLOG.md` | git, `PPA-n` IDs | — |
| CI-13 | Data dictionary | `docs/data_dictionary.md` | git | — |
| CI-14 | Dashboard application | `app/` | git | — |
| CI-15 | Build, run and environment definition | `Makefile`, `pyproject.toml`, `.env.example` | git | — |
| CI-16 | Continuous-integration definition | `.github/workflows/ci.yml` | git | — |

Two deliberate choices in that table:

- **CI-07 and CI-08 are not under version control.** Data is reproducible from
  the APIs and from `make build`, so the repository stores the *means* of
  producing it, not the bytes. `.gitignore` keeps the folders and drops the
  contents. The cost is that reproducing an old baseline exactly depends on the
  upstream APIs still serving the same history; see §6.
- **CI-06 is under version control**, because `netztransparenz_market_values_monthly.csv`
  is a published reference series used to check the model. It must not move
  underneath a baseline.

### 2.2 The single-source rule for assumptions

`config/project.toml` opens with the rule the project is built on:

> One place for every assumption the pipeline makes. Code reads this file via
> `ppa_lab.config.load_settings()`; nothing below should be hard-coded elsewhere.

This is configuration identification doing real work: there is exactly one place
to look to know what the model assumed, and changing an assumption is a change to
one tracked file rather than a hunt through 57 modules.

### 2.3 Version schemes

Three things carry versions, independently and on purpose:

| Item | Scheme | Current |
|---|---|---|
| CI-01 code | [Semantic Versioning](https://semver.org/) in `pyproject.toml` | `1.16.0` |
| CI-03 methodology | own version line in `METHODOLOGY.md` | `1.11` |
| Release baseline | annotated git tag `vX.Y.Z` | `v1.16.0` |

**The methodology version deliberately lags the code version.** A release that
re-anchors the forward curve to newer market quotes changes every number without
changing the method, so `METHODOLOGY.md` stays where it is. The v1.16.0 changelog
entry records exactly this: *"the methodology's version stays 1.11 (no change to
the method)."* Keeping the two apart means "did the method change?" and "did the
numbers change?" are separate questions with separate answers. The scheme only works when the
line is bumped: `v1.11.0` changed the method without bumping it, and the six
baselines `v1.11.0` – `v1.15.0` under-report the method by one version
(see [BASELINES.md](BASELINES.md) §2.1).

---

## 3. Configuration change management

### 3.1 The change path

```
   change request            →  docs/BACKLOG.md, ticket PPA-n with acceptance criteria
   decision (if structural)  →  docs/decisions/NNNN-*.md, an ADR
   implementation            →  commit(s) referencing PPA-n
   verification              →  make test, make check, CI on push and pull request
   release                   →  version bump, CHANGELOG entry, annotated tag vX.Y.Z
   closure                   →  BACKLOG status set to Done (version)
```

### 3.2 Change requests

Every change starts as a ticket in `docs/BACKLOG.md`. The backlog states the rule
for closure:

> Each ticket has acceptance criteria (AC): it is done only when all AC are met,
> tests pass and the learning-track page for that step is written.

Tickets use stable IDs (`PPA-1` … `PPA-9`, with `PPA-8b`, `PPA-8c` … for
follow-on work). The ID appears in the commit, in the CHANGELOG entry and in the
tag message, so a change is traceable in both directions: from a ticket to the
code that implemented it, and from any released baseline back to the request that
caused it.

### 3.3 Decisions

A change that commits the project to a structural choice — which data source is
authoritative, how timestamps are stored, how the data layers are split — gets an
Architecture Decision Record in `docs/decisions/`, numbered sequentially, with
fields `Status`, `Date` and `Ticket`, then `Context`, `Decision` and
`Consequences`. ADRs are append-only: a superseded decision is marked superseded,
not deleted, so the reasoning behind an old baseline stays readable.

### 3.4 Verification before merge

`.github/workflows/ci.yml` runs on every push and every pull request:

- `ruff check src tests app` — style, imports, common bugs
- `pytest --cov=ppa_lab` — the full offline suite with coverage

Tests that call live APIs are marked `network` and deselected by default
(`addopts = "-q -m 'not network'"`), so the suite is deterministic and CI never
fails because an upstream API is down. Contract tests against the real APIs run
deliberately, via `make test-network`.

### 3.5 Release

A release bumps the version in `pyproject.toml`, adds a CHANGELOG section stating
what changed and why, and is marked with an annotated git tag. The tag message
carries the ticket and a one-line description of the baseline.

---

## 4. Configuration status accounting

### 4.1 What is recorded where

| Question | Answer lives in |
|---|---|
| What changed in this release, and why? | `CHANGELOG.md` |
| Which ticket caused it? | `CHANGELOG.md` heading and the commit subject |
| What was the exact state of the project at that release? | the annotated tag `vX.Y.Z` |
| Was the method changed, or only the inputs? | the `METHODOLOGY.md` version at that tag |
| What did the model produce at that release? | `reports/` and `reports/results.json` at that tag |
| What is still open? | `docs/BACKLOG.md` status column |

### 4.2 Release baselines

27 baselines are tagged, `v0.1.0` through `v1.16.0`. Each is an annotated tag
whose message names the ticket and describes the baseline. Any of them can be
retrieved:

```bash
git show v1.5.0:METHODOLOGY.md | head -5     # the method as it stood
git show v1.0.0:pyproject.toml | grep version # the code version
git checkout v1.11.0                          # the whole baseline
```

The version history is not strictly sequential, and that is correct rather than a
mistake: **there is no 0.8.0.** Step 9 (the memo and dashboard, `PPA-9`) shipped
before Step 8 (hedging, `PPA-8`), so the releases run `0.7.0 → 0.9.0 → 1.0.0`.
The gap records the order the work actually happened in.

Code version and methodology version at each baseline:

| Baseline | Code | Methodology |
|---|---|---|
| `v1.0.0` | 1.0.0 | 1.0 |
| `v1.5.0` | 1.5.0 | 1.5 |
| `v1.11.0` | 1.11.0 | 1.10 |
| `v1.16.0` | 1.16.0 | 1.11 |

---

## 5. Configuration verification and audit

Three layers, all automated.

### 5.1 Unit and integration tests

310 tests in 43 modules under `tests/` (plus `conftest.py` for shared fixtures),
run by `make test` and by CI on every push and pull request. Fixtures under `tests/fixtures/` hold saved API responses so the suite is
offline and deterministic.

### 5.2 Data-quality checks

`make check` runs the checks in `src/ppa_lab/data/quality.py` and **fails on any
FAIL**. The result is written to `reports/data_quality.md`, so the data-quality
state of a baseline is part of that baseline.

### 5.3 Reconciliation against published market values

This is the strongest verification the project has. `config/project.toml` holds
**29 `[[reconciliation]]` entries**, each naming a metric, a year, the officially
published value, a tolerance and the source:

```toml
[[reconciliation]]
metric = "mean_price_eur_mwh"
year = 2024
value = 79.46
tolerance = 0.5
source = "netztransparenz.de Jahresmarktwert JW 2024 = 7.946 ct/kWh"
```

The model is checked against values it does not control, published by the German
TSOs and the Bundesnetzagentur. Where a year does not match, the deviation is
recorded with its explanation rather than the tolerance being widened — the 2024
entry carries a note identifying June 2024 as the entire source of the
difference, every other month matching to 0.000 ct/kWh.

### 5.4 Audit procedure

To audit a baseline:

```bash
git checkout vX.Y.Z
make setup
make data          # rebuild CI-07 from the APIs
make build         # rebuild CI-08
make check         # data-quality gate; fails on any FAIL
make test          # the offline suite
make all           # regenerate every report
git diff --stat    # committed reports vs freshly generated ones
```

A clean `git diff` means the baseline reproduces. §6 lists the two reasons it
might not.

---

## 6. Limitations

Stated plainly, because a configuration management plan that oversells its own
controls is worse than none.

1. **There is no independent approval authority.** This is a single-maintainer
   project. "Approval" means the maintainer reviewing their own change, with CI
   as the only impartial gate. There is no Change Control Board, no separation
   between requester and approver, and no second reviewer. In any organisational
   setting that separation is most of what configuration change management *is*;
   here it is absent.

2. **The tags were applied retroactively.** All 27 were created on 2026-11-16
   from `CHANGELOG.md`, mapped to their commits via the `PPA-n` ticket IDs, not
   at the time each release was made. Each tag's date is set to its original
   commit date so the chronology reads correctly, and every tag message says it
   was tagged retroactively. The mapping was checked against the `pyproject.toml`
   and `METHODOLOGY.md` versions committed at each point, which agree. Releases
   from here on are tagged at the time.

3. **Exact reproduction of an old baseline depends on upstream APIs.** CI-07 and
   CI-08 are not under version control. Reproducing `v0.3.0` requires
   Energy-Charts, ENTSO-E and Open-Meteo to still serve the same history. They
   are stable public series and the tests run offline from fixtures, but the
   project does not archive the raw bytes, so bit-exact reproduction is not
   guaranteed indefinitely.

4. **Reports are generated artefacts that are also committed.** `reports/` is
   both an output of `make all` and a tracked configuration item. This is
   deliberate — it makes each baseline's published numbers visible without
   running anything — but it means the repository can hold reports that are
   newer or older than the code if a release is made carelessly. The audit in
   §5.4 is what catches that.

5. **This plan was written from the published function breakdown of EIA-649 and
   ISO 10007, not from licensed copies of the standards.** Both are paid
   documents. The five functions, their names and their scope are publicly
   documented; the detailed requirements inside each standard are not reproduced
   or claimed here.

---

## 7. Changes to this plan

This document is itself a configuration item. Changes to it go through the same
path as any other change: a ticket in `docs/BACKLOG.md`, a commit, and a
`CHANGELOG.md` entry.

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-11-16 | First issue. Documents the scheme already in use; adds the configuration item register, the 27 tagged baselines and the audit procedure. |
