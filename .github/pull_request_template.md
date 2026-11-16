<!--
The change submission. Everything a reviewer needs to accept this into a
baseline, in one place. See CONTRIBUTING.md §2.5.
-->

## Ticket

`PPA-n` — <!-- link or quote the backlog line -->

## What changed, and why

<!-- A sentence or two. The CHANGELOG entry is written from this. -->

## Impact on published numbers

<!--
State old -> new for every number this moves (reports/, results.json, memo,
dashboard, README). Write "none" if nothing moves — a blank reads as "not
checked".
-->

| Number | Before | After |
|---|---|---|
| | | |

## Verification

- [ ] `make lint` clean
- [ ] `make test` passes
- [ ] `make check` passes (data-quality gate; fails on any FAIL)
- [ ] CI green
- [ ] New or changed behaviour is covered by a named test
- [ ] Affected steps re-run and regenerated reports committed (if numbers moved)
- [ ] `make test-network` run (only if an API client changed)

### Tests covering this change

<!-- file::function, one per line. These go into TRACEABILITY.md. -->

## Configuration management

- [ ] New assumptions are in `config/project.toml`, with source and date — not hard-coded
- [ ] `METHODOLOGY.md` version bumped **only if the method changed** (leave it alone otherwise)
- [ ] `TRACEABILITY.md` updated for any new or changed acceptance criteria
- [ ] ADR added or updated, if the change is structural
- [ ] No data, secrets or hand-edited reports committed
- [ ] No reconciliation tolerance widened to make a check pass

## Release

- [ ] Not a release — merging only
- [ ] Release: version bumped, `CHANGELOG.md` entry added, backlog status set to Done, annotated tag to follow, `BASELINES.md` row added

## Anything a reviewer should look at closely

<!--
Where you are least confident. On a single-maintainer project this is the part
that does the most work — it is the only place a self-review gets to be honest
about what it did not fully check.
-->
