# Public hard-negative pairs v1 — Data Card

This package contains 345 binary training pairs derived from
70 frozen ranker-training queries. Each row has one sanitized query
projection, one positive rendered catalog text, one wrong-candidate rendered catalog text, binary
labels, a bounded negative category, and package-local IDs.

The examples reveal the training text and therefore reveal effective training membership. The
package removes direct private case/source IDs, URLs, contact handles, known seller/platform names,
secrets, local paths, image metadata, API responses, selection rows, calibration rows, and
final/holdout rows;
it does not claim that publication makes membership secret or anonymous.

Mining is deterministic and one-shot over the frozen T2 Top-25 pools. Evidence-insufficient
same-family siblings are held instead of being forced to label 0. The labels mean "wrong relative
to the frozen catalog identity for this query"; they are not manufacturer-certified or global
truth. No model training, model selection, calibration, final evaluation, or runtime activation
was performed by this package build.
