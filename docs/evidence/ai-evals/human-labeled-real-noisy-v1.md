# Human-labeled real-noisy name corpus — v1

## Evidence scope

`data/human_labeled_names.json` is a frozen auxiliary dataset derived from the locally reviewed
`labeling-queue.csv`. The import used only rows not marked `excluded` and required every included
row to have a confirmed human candidate name, casting name, and pricing keyword.

The resulting corpus contains 101 confirmed records. Ninety-one preserve both the recognition
provider's first candidate name and the human-verified name. Ten preserve a null initial name with
`initial_output_status="no_candidate"`; these remain useful recognition-failure examples rather
than being silently removed. Four excluded source rows were omitted.

## Data boundary and decision

The source labels identify names but do not yet establish an immutable mapping to Product Variant
Resolver's catalog UUIDs and slugs. For that reason, this corpus is eligible for candidate-name and
normalization evaluation, plus future catalog alignment, but not for canonical-resolution accuracy,
calibration training, or threshold selection. Existing fixture-v1 metrics are unchanged.

The importer keeps the first recognition name and confidence, selected keyword outputs from the
deterministic and AI variants, human-confirmed structured name fields, failure categories, and a
stable case ID. It intentionally omits local frame paths and does not copy the source images. The
manifest freezes the source filename, source checksum, generated dataset checksum, row counts, and
the number of explicit no-candidate failures.

## Verification

- `python scripts/import_human_labeled_names.py --source <labeling-queue.csv>` deterministically
  regenerates the repository-owned JSON and manifest.
- `python scripts/validate_fixture_data.py` checks the frozen checksum, record count, unique case
  IDs, confirmed labels, required names, and consistency between the initial name and status.
- `python -m unittest tests.test_human_labeled_names -v` checks the 101/91/10/4 accounting and
  confirms the corpus remains outside canonical accuracy and calibration gates.
