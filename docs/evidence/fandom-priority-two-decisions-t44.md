# T44 Final Priority-Two Owner Decisions — Verification Evidence

## Scope and result

T44 applies the project owner's authorization to the exact nine-family T43 research packet. Six
recommendations become accepted `create_new_casting` family decisions: Proton Saga, Small Bloc,
Super Twin Mill, The Vanster, Twin Mill Gen-E, and X-34 Landspeeder. Nissan Skyline GT-R (BNR32),
Power Wheels Dune Racer, and Standard Kart become completed holds with their original evidence and
reasons intact.

The cumulative review queue is now `adjudicated`: 53 of 53 family decisions are completed, with 4
accepted existing-family merges, 42 accepted new-family decisions, and 7 holds. All 100 staged Wiki
release rows remain variant-held, promotion eligibility is zero, and no stable catalog UUID,
canonical variant, PostgreSQL row, runtime candidate, calibration input, or evaluation label was
created or changed.

## Decision and derived artifacts

- Decision batch SHA-256: `a5dc269b2ced7b8423fd0cf321ab470922c12b7520c88944f99539cbdad2626b`
- Cumulative queue SHA-256: `989bc914f9493051a071472c9defd352fe1cb8cc217c062e1f479bdcb9c6e4d8`
- Readable result SHA-256: `245ded3d564a94eccc017a942189eb38a40f4c5a08652d724be3dc759e2ddb10`
- Queue manifest SHA-256: `6b532978c86adf39dbc2f41222d41ca9b765b1c615dce5453a0ba04955a9f6ff`

The decision input remains separate from the generated queue and report. The resulting queue keeps
all five earlier owner batches, appends the new event as history entry six, and retains the original
research packet references for attribution.

## Focused validation

```text
PYTHONPATH=src /opt/homebrew/bin/python3 -m unittest \
  tests.test_fandom_priority_two_decisions_batch_five -v

Ran 6 tests — OK
```

The focused tests require exact 6-create/3-hold coverage, exact current-family and release-row
scope, prior-decision/history preservation, family-only authorization, variant hold, deterministic
output hashes, and fail-closed behavior for altered, incomplete, duplicate, or widened batches.

## Full validation

```text
PYTHONPATH=src /opt/homebrew/bin/python3 -m unittest discover -s tests -p 'test_*.py' -q
Ran 159 tests in 1.440s — OK
```

The machine-wide Python 3.14 interpreter emitted the previously documented Starlette warning about
legacy `httpx`. The project's constrained Python 3.12 container path was previously verified with
`httpx2`; the warning did not fail or alter this run.

The following checks all exited zero:

- fixture and 100-row pilot validation;
- deterministic pilot review, base queue, priority-one evidence, and priority-one decisions;
- all five priority-two research `--check` commands;
- all five cumulative priority-two decision `--check` commands;
- Python compilation for `src`, `scripts`, `tests`, and `migrations`;
- default and PostgreSQL-profile Docker Compose configuration;
- `git diff --check`.

The five cumulative decision checkpoints reproduced 14/39, 24/29, 34/19, 44/9, and finally 53/0
completed/pending families. Promotion eligibility remained zero at every checkpoint.

## Remaining boundary

This evidence closes the family-adjudication stage, not the materialization stage. The next safe
step is to specify how accepted family outcomes receive deterministic review IDs, aliases,
lineage/provenance, and hold exclusions before any record enters the human-backed retrieval source
or PostgreSQL. Release-variant adjudication remains a separate future step.
