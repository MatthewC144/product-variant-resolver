# Generated Reports

This directory contains rendered or aggregate outputs from historical evaluations, selection runs,
catalog reviews, storage experiments, and data-preparation workflows.

- Reports are evidence, not active configuration.
- Many files are checksum-bound by manifests or tests and must not be reformatted manually.
- Large `selection.json` and `historical-calibration.json` files preserve negative-result lineage.
- A newer report does not automatically authorize a model or runtime change.

Start with [Results](../docs/RESULTS.md) for conclusions. Enter this directory only when validating
the exact report behind a result, then follow its adjacent manifest/spec/evidence links.

Generated scratch output belongs under ignored `reports/generated/`; do not commit ad hoc reruns.

