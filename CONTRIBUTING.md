# Contributing

How a change gets into this project: what to open, what to prove, and what to
record. The reasoning behind the scheme is in
[CONFIGURATION_MANAGEMENT.md](CONFIGURATION_MANAGEMENT.md); this is the
practical version.

> **One maintainer.** Review here means the maintainer reviewing their own
> change, with CI as the only impartial gate. There is no second approver. The
> checklists below exist because that is a weak control and a written procedure
> is the next best thing — see `CONFIGURATION_MANAGEMENT.md` §6.1.

---

## 1. Setup

```bash
make setup          # virtual environment + project + dev tools
make test           # the offline suite (310 tests, no network)
make lint           # ruff: style, imports, common bugs
make help           # every target with a one-line description
```

Copy `.env.example` to `.env` for the optional API keys. ENTSO-E and
netztransparenz.de need free credentials; Energy-Charts and Open-Meteo do not.
**Never commit `.env`.** The tests run offline from saved fixtures, so you do not
need any key to contribute.

---

## 2. The change path

```
1. Change request   →  a ticket in docs/BACKLOG.md with acceptance criteria
2. Decision         →  an ADR in docs/decisions/, if the change is structural
3. Implementation   →  commits referencing the ticket
4. Verification     →  make lint && make test && make check, plus CI
5. Traceability     →  map new acceptance criteria to tests in TRACEABILITY.md
6. Release          →  version bump, CHANGELOG entry, annotated tag
7. Closure          →  ticket status set to Done (version)
```

### 2.1 Raise a change request first

Every change starts as a ticket in [docs/BACKLOG.md](docs/BACKLOG.md), using the
next free `PPA-n` identifier (follow-on work on an existing ticket gets a letter
suffix: `PPA-8`, then `PPA-8b`, `PPA-8c`). Add a row to the summary table and a
block with a story and **acceptance criteria**.

Acceptance criteria are the contract. The backlog's own rule:

> Each ticket has acceptance criteria (AC): it is done only when all AC are met,
> tests pass and the learning-track page for that step is written.

Write them so each one can fail. "Improve the price model" cannot. "Parameter
recovery on synthetic prices with known parameters" can, and does — see
`tests/test_price_model.py`.

A template is in [`.github/ISSUE_TEMPLATE/change_request.md`](.github/ISSUE_TEMPLATE/change_request.md).

### 2.2 Record structural decisions as ADRs

If the change commits the project to a choice that would be expensive to
reverse — which data source is authoritative, how timestamps are stored, how the
data layers are split — add an Architecture Decision Record in
[`docs/decisions/`](docs/decisions/), numbered sequentially, using
[`docs/decisions/TEMPLATE.md`](docs/decisions/TEMPLATE.md).

ADRs are append-only. A decision that is later replaced is marked
`superseded by ADR NNNN`, never deleted, so the reasoning behind an old baseline
stays readable.

### 2.3 Put assumptions in the configuration, not the code

`config/project.toml` holds every assumption the pipeline makes, and its header
states the rule:

> One place for every assumption the pipeline makes. Code reads this file via
> `ppa_lab.config.load_settings()`; nothing below should be hard-coded elsewhere.

A new parameter goes there with a comment saying what it is, where it came from
and when. A market quote also records its date and source — see
`[price_model] forward_eur_mwh` / `forward_date` / `forward_source`. Adding a
magic number to a module instead is the one change most likely to be rejected.

### 2.4 Commit messages

Two shapes, both in use:

```
feat(pricing): PPA structures, fair prices and 2024-2025 back-test (PPA-3)
v1.11.0 (PPA-8f): solar and storage build-out scenarios after 2027
```

The first for work within a release, the second for the release commit itself.
Always name the ticket. Use a bulleted body for anything that changes published
numbers, stating the old and the new value — `CHANGELOG.md` is written from
these. Keep the attribution trailer the project already uses when AI tooling
assisted the change.

### 2.5 Verification before merge

```bash
make lint      # must be clean
make test      # 310 tests, offline
make check     # data-quality gate; fails on any FAIL
```

CI runs `ruff check src tests app` and `pytest --cov=ppa_lab` on every push and
pull request. Tests touching live APIs are marked `network` and deselected by
default; run them deliberately with `make test-network` when you change a
client.

**A change that alters published numbers must also re-run the affected steps**
(`make prices scenarios pricing hedging memo`, or `make all`) and commit the
regenerated reports. Reports are tracked configuration items; leaving them stale
makes the baseline inconsistent with its own code.

### 2.6 Keep traceability current

If the change adds or alters acceptance criteria, update
[TRACEABILITY.md](TRACEABILITY.md) in the same commit: map each new criterion to
the test that verifies it, or mark it `R` if it is a documentation deliverable
with no automated check. Nothing enforces this — see `TRACEABILITY.md` §3.6 — so
it depends on doing it at the time.

A pull-request checklist is in
[`.github/pull_request_template.md`](.github/pull_request_template.md).

---

## 3. Releasing

A release is a new baseline. The checklist:

1. **Version** — bump `version` in `pyproject.toml` (semantic versioning: patch
   for fixes, minor for new capability, major for a breaking change to the
   public interface).
2. **Methodology** — bump the version line in `METHODOLOGY.md` **only if the
   method changed.** A release that re-anchors the forward or rebuilds the
   dashboard leaves it alone. Eight baselines deliberately carry a method
   version older than their code; see [BASELINES.md](BASELINES.md) §2.1.
3. **Reports** — re-run the affected steps and commit the regenerated reports and
   `reports/results.json`. Check that `ppa_lab_version` in `results.json` matches
   the version you just set.
4. **Changelog** — add a `## [X.Y.Z]` section to `CHANGELOG.md` stating what
   changed and **why**, with old and new values for any published number.
5. **Backlog** — set the ticket's status to `**Done** (vX.Y.Z)`.
6. **Tag** — an annotated tag at the release commit:
   ```bash
   git tag -a v1.17.0 -m "ppa-lab v1.17.0

   Ticket PPA-n: one line on what this baseline is."
   ```
   Tag at the time of release. The 27 existing tags were applied retroactively
   on 2026-11-16 and say so in their messages; that is a one-off, not the
   procedure.
7. **Baseline record** — add a row to [BASELINES.md](BASELINES.md) and re-run the
   integrity checks in its §3.

---

## 4. What not to do

- **Do not commit data.** `data/raw/` and `data/processed/` are git-ignored and
  rebuildable with `make data build`. `data/reference/` is tracked on purpose —
  it holds published reference series the model is checked against, and it must
  not move underneath a baseline.
- **Do not commit secrets.** `.env` is ignored. API keys never belong in
  `config/project.toml`, in a fixture or in a commit message.
- **Do not widen a reconciliation tolerance to make a check pass.** The 29
  `[[reconciliation]]` entries check the model against officially published
  values. If a year stops matching, find out why and record the cause in a
  `note` — as the 2024 entry does, identifying June 2024 as the entire source of
  the difference. A tolerance widened to hide a deviation removes the only
  independent check the project has.
- **Do not edit a report by hand.** Reports are generated. Fix the code or the
  configuration and regenerate.
- **Do not rewrite history behind a tag.** A published baseline must stay
  retrievable.

---

## 5. Where things are

| | |
|---|---|
| What the project is and what it concludes | [README.md](README.md) |
| The method, and its limits | [METHODOLOGY.md](METHODOLOGY.md) |
| Every assumption the pipeline makes | [config/project.toml](config/project.toml) |
| Tickets and acceptance criteria | [docs/BACKLOG.md](docs/BACKLOG.md) |
| Structural decisions | [docs/decisions/](docs/decisions/) |
| What changed in each release | [CHANGELOG.md](CHANGELOG.md) |
| What each baseline was made of | [BASELINES.md](BASELINES.md) |
| Which test verifies which requirement | [TRACEABILITY.md](TRACEABILITY.md) |
| How configuration and change control work | [CONFIGURATION_MANAGEMENT.md](CONFIGURATION_MANAGEMENT.md) |
| Field definitions for every dataset | [docs/data_dictionary.md](docs/data_dictionary.md) |
