# T07 PostgreSQL Catalog Ingestion Evidence

> Date: 2026-09-06  
> Mode: Lite / isolated local Docker verification  
> Catalog: `fixture-v1`

The verification used Compose project `pvr-t07`, host port `55433`, PostgreSQL 16 with pgvector,
and the rebuilt `product-variant-resolver:lite` Python 3.12 image. The database started with an
empty migrated application schema. No existing project database or persistent user volume was
used.

`scripts/verify_postgres_ingestion.py` performed four checks through the production
`PostgresCatalogRepository`:

1. Ingest the complete fixture catalog once.
2. Ingest the identical catalog again and compare every stored row, including surrogate IDs and
   timestamps.
3. Modify one product and introduce a conflicting canonical ID later in the same import, then prove
   that the earlier modification was rolled back.
4. Submit a 119-product snapshot to a 120-product database and prove that the missing product was
   not interpreted as an implicit deletion and metadata was not changed.

The final structured result was:

```json
{
  "collision_rolled_back": true,
  "first_ingestion": {
    "identifier": 120,
    "index_metadata": 1,
    "product_alias": 240,
    "product_embedding": 0,
    "product_search": 120,
    "product_variant": 120,
    "provenance_record": 120
  },
  "implicit_deletion_refused": true,
  "repeated_ingestion_identical": true,
  "status": "passed"
}
```

`product_embedding` remains empty by design. T07 installs catalog facts and sparse-search source
documents; T10 owns versioned vector materialization. The current API also remains on the offline
backend because T09/T10 PostgreSQL query execution is not implemented.

The first container verification attempt failed before database writes because the verification
entrypoint passed the `PVR_CATALOG_PATH` environment string directly to a loader requiring a
`Path`. The boundary was corrected by converting the environment value explicitly, the image was
rebuilt, and the complete verification then passed twice, including the strengthened missing-row
check. The isolated container, network, and named volume were removed afterward.
