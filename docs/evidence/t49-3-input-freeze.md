# T49.3 HSP-1 — Approved input freeze evidence

2026-09-14. Lite, main agent; no subagents. Verdict: scoped G1 and HSP-1 PASS only.
Owner「開始執行」followed the task/budget confirmation question asking to start HSP-1.
Exact three-confirmation/spec anchors: [approval ledger](../../specs/human-storage-profile-development/approval.md).
This does not authorize the separate new isolated SQL run, default rollout or production writes.

## Published inputs and provenance

Directory: `data/evaluation/human-storage-profile-development-v1/freeze/`. Eight files:
original approved requirements/design/tasks/protocol-draft bytes, `approval.json`, `protocol.json`,
`declared-profile.json`, `manifest.json`. Historical headings/flags remain in original copies;
new approval/protocol records describe subsequent confirmations and override publication states.
Specs are fetched at explicit committed versions and SHA-checked, not copied from mutable checklists.

Producer committed BEFORE publication: `448f9c0b498b3372f28e03059aa2cf6a816ce512`,
`scripts/freeze_human_storage_development.py` SHA-256
`fcbbc5279fbebe81f85b9ccdc58d8b04d2f04324db356460e9fef6572f7f9959`.
Manifest verifies26existing input byte hashes:11baseline sources/report, original142doc plan,
12pinned source files and199dev pack/manifest. It reads hashes/data but builds no retrieval index.
No final105question data is loaded. The old math protocol remains distinct from the new storage one.

| Frozen artifact | SHA-256 |
|---|---|
| protocol.json | d42ba490dccc8ab6b38f1087d39867d22e0e3e4990c40932da03c552ad2e6fd4 |
| manifest.json | aa64eb421af6457ad210a96b24e3599c70d10b0f30b7fd58ecf87174a4b90145 |
| declared-profile.json | e0e9dac61c440b5fe45e2759f3311c466ed623fd1dda5eb86dd9cc2b62592325 |
| approval.json | 97b864febb7be18d016151b4b6d3ef9e60672afcc239ad8a673d056124b3d070 |

`approved_spec_sha256` is `069e1cc4209ce2ffbf2276027feb7f036c18639e210cca16cd0ea87ae29794b2`:
SHA of canonical sorted/indented UTF-8 JSON (trailing newline) of the four source commit/path/SHA
bindings; individual approved file bytes are separately pinned. Protocol status is
`approved_inputs_frozen_pending_adapter_and_runtime`; `ready_for_real_outputs=false`.
Adapter/import manifest and runtime IDs are null, honestly pending HSP-2. The manifest declares
future all-imported-source/runtime/run-approval binding mandatory before real outputs, not complete now.

## Actually executed verification

- `.venv/bin/python scripts/freeze_human_storage_development.py --freeze`: PASS once after producer commit.
- `.venv/bin/python scripts/freeze_human_storage_development.py --check`: PASS, no SQL/HTTP/retrieval.
- `.venv/bin/python -m pytest tests/test_human_storage_development_freeze.py`:16PASS.
  Private temp copies/mocked producer tests cover deterministic protocol/exposure flags, equality,
  repeat refusal, input changes, altered spec/producer bytes, tampered/partial/extra/symlink bundles,
  invalid commit rejection and forbidden network. They are not runtime/SQL experiments.
- Initial `.venv/bin/python -m pytest`:488PASS/1FAIL; subprocess package import lacked PYTHONPATH.
  Failure: `tests/evaluation/test_human_knowledge_evaluation.py` reproducible-report check,
  `ModuleNotFoundError: product_variant_resolver`. No old code or assertion changed.
- Correct invocation `PYTHONPATH=src .venv/bin/python -m pytest`:489PASS, one existing
  Starlette/AnyIO BlockingPortal deprecation warning,14.22seconds test-suite duration (not profile latency).
- Ruff `--select F,I` on new script/tests and isolated strict MyPy `--follow-imports=skip` on script:PASS.
- `git diff --check`:PASS. Existing src/migration/config/default/data/old supervisor source diff empty.

## Boundaries and carry

Exclusive publication refuses an existing directory and validates inputs before output creation.
Killed/failed publication may leave a partial bundle; checks reject it and publication never replaces
it. This is byte-verifiable, Git-audited immutability, not OS write protection or crash-atomic storage.
No credentials, SQL/DB resources, real199paired requests, final replay, new costs/accuracy or3kclaim.
HSP-2 new profile/app implementation and actual-source/runtime freeze next; HSP-3 SQL run approval
still required. Full T49.3/HSP2–4/T49.4 remain incomplete. Existing canonical authority is unchanged.
