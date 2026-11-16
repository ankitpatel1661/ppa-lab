---
name: Change request
about: Propose a change to the model, data, pipeline or documentation
title: "PPA-n: "
labels: change-request
---

<!--
A change request becomes a ticket in docs/BACKLOG.md. Use the next free PPA-n
identifier; follow-on work on an existing ticket takes a letter suffix
(PPA-8 -> PPA-8b). See CONTRIBUTING.md §2.1.
-->

## Ticket

`PPA-n` — <!-- one line: what this changes -->

## Story

As a <!-- role --> I want <!-- capability --> so that <!-- why it matters -->.

## Acceptance criteria

<!--
Write each one so it can FAIL. "Improve the price model" cannot be verified;
"parameter recovery on synthetic prices with known parameters" can.
Mark documentation deliverables explicitly — they are verified by review only.
-->

- [ ]
- [ ]
- [ ]

## Configuration items affected

<!-- Tick what this change touches. IDs from CONFIGURATION_MANAGEMENT.md §2.1. -->

- [ ] CI-01 source code (`src/ppa_lab/`)
- [ ] CI-02 assumptions and parameters (`config/project.toml`)
- [ ] CI-03 methodology (`METHODOLOGY.md`) — **does the method itself change?**
- [ ] CI-04 reconciliation tolerances (`[[reconciliation]]`)
- [ ] CI-05 tests and fixtures (`tests/`)
- [ ] CI-06 committed reference data (`data/reference/`)
- [ ] CI-09 / CI-10 reports and figures (`reports/`)
- [ ] CI-11 decision records (`docs/decisions/`)
- [ ] CI-13 data dictionary
- [ ] CI-14 dashboard (`app/`)
- [ ] CI-15 / CI-16 build, environment or CI definition

## Impact on published numbers

<!--
Does this change any number in reports/, results.json, the memo, the dashboard
or the README? If yes, say which and give the expected direction. If no, say so
explicitly — that is a meaningful statement, not a blank.
-->

## Verification plan

<!-- Which tests will prove this? Name them if they exist, describe them if not. -->

## Structural decision needed?

- [ ] No
- [ ] Yes — an ADR will be added to `docs/decisions/` (see `docs/decisions/TEMPLATE.md`)

## Open questions

<!-- Anything undecided. Say so rather than guessing in code. -->
