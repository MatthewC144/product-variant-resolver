# Representative hard benchmark v1 — source baseline

Date: 2026-09-26. Mode: Lite / Lean Industrial. Scope: **RHB-T1 only**.

## Outcome

The current source evidence is now checksum-bound and machine-checkable without network access. This
baseline records availability and authority boundaries; it does **not** approve sources for the
representative pilot, publish private owner rows, create benchmark labels, or promote any row into
canonical identity. The owner source Gate remains pending for RHB-T3.

| Evidence source | Count | Current publication reality | Prospective RHB-v1 use / redistribution | Exact authority |
|---|---:|---|---|---|
| `fixture-v1` benchmark | 100 | row-level public | both pending T3 selection | synthetic only |
| `fixture-v1` catalog | 120 | row-level public | both pending T3 selection | synthetic only |
| Human-labeled scans | 101 | **row-level public and Git-tracked** | both blocked pending T3 rights/privacy decision | none |
| Human alignment | 101 | **row-level public and Git-tracked** | both blocked pending parent-rights decision | **0 exact**, 2 family-only, 99 unmapped |
| Owner release snapshot | 1,763 | public aggregate only; private rows unpublished | use and redistribution blocked pending T3 | none |
| Checked-in Wiki pilot | 100 | attributed row-level public | both pending T3; new collection blocked | none |

## Why these boundaries exist

- A human-confirmed casting name does not prove an exact release variant, year, color, series, or
  collector number. The alignment therefore preserves `0 exact / 2 family-only / 99 unmapped`.
- The human-label JSON and its derived alignment are already Git-tracked in the public repository.
  The inventory records that existing publication as fact while separately keeping future benchmark
  reuse and republication blocked until the T3 rights/privacy decision. Existing publication is not
  interpreted as permission for a new use.
- The 1,763 owner rows have an unpublished, gitignored raw source. This public baseline uses only the
  Git-tracked `reports/local-release-staging-v1/manifest.json` aggregate and its non-reversible
  source-content digest; it neither requires the ignored local review summary nor copies any row or
  casting label. A clean checkout can therefore reproduce this baseline.
- The Wiki pilot is attributed text under its recorded license, but every row remains outside
  canonical truth and evaluation labels. Its presence does not authorize a new crawl.
- Every owner decision is still `pending` until RHB-T3; affected prospective uses are explicitly
  blocked while that decision and its required rights/privacy evidence are absent.

## Reproduction

```bash
python3 scripts/build_representative_hard_benchmark_source_inventory.py --check
```

The command reads repository-local files only. A successful check prints `unchanged`; any changed
count, parent checksum, alignment authority, staging boundary, or stored output fails closed.

## Frozen artifacts

- Inventory SHA-256: `c56a6e657b61682f66a6ebdd7fc1794380feb21d8e1906beae072f06df92c816`
- Fixture benchmark SHA-256: `e46c5b4a405a5b3e9fbac35c9613d8e5945e2d4494ad8df9f3d8be1e352fc323`
- Fixture catalog SHA-256: `0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261`
- Human scan dataset SHA-256: `68b5dfdb8d0fa4972328d172cc5a56d78ac8bf00bc740083b2bfc07eb2a91188`
- Alignment SHA-256: `d1a6d3798dec7a5e1258a74b95294bd2f50e81d7c78db2eb29a151917e7499b6`
- Owner private snapshot content SHA-256: `85dae23a1a302845f59b63450b9d90623b4c9893ddcde672bffc8eb5b53849af`
- Wiki normalized SHA-256: `e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6`
- Network requests: `0`
- Private source rows copied: `false`
