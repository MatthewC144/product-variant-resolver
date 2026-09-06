# Python dependency constraints

`python312.txt` freezes the compatibility-sensitive API and reporting versions from the verified
Python 3.12.14 Docker stack. It adds an AnyIO 4.14.0 compatibility pin that was separately tested
under local Python 3.12 to keep TestClient warning-free; a no-cache Docker rebuild remains required
to promote that addition to container evidence. The Docker build applies the file with pip's `-c`
option while `pyproject.toml` remains the source of truth for direct dependencies and supported
version ranges.

This is a selective constraints strategy, not a complete transitive lock. It prevents an ordinary
image rebuild from silently changing FastAPI, Starlette, TestClient's `httpx2` transport, AnyIO,
Pydantic, or Uvicorn. AnyIO is included because 4.15 deprecated an alias that Starlette 1.6 still
imports, producing a warning during TestClient collection. PostgreSQL extras and packaging/build
dependencies still resolve within the bounded ranges declared in `pyproject.toml`; they must not be
described as fully reproducible until the PostgreSQL runtime path is implemented and verified.

The Docker base uses the verified `python:3.12.14-slim` patch tag instead of the moving
`python:3.12-slim` tag. It intentionally does not use a platform-specific image digest, so the same
Dockerfile remains usable on both ARM64 and AMD64; controlled rebuilds are still needed for base OS
security updates.

To update the constraints:

1. Resolve a candidate set under Python 3.12 without editing this file in place.
2. Run the full test suite and confirm importing `fastapi.testclient` emits no warning.
3. Rebuild the image without Docker cache and run the API/reporting checks as the non-root user with
   the read-only root filesystem.
4. Replace the constrained versions together and record the evidence and trade-off in the project
   log. Do not update only Starlette, AnyIO, or the `httpx2` transport.

For a matching local development environment, install the dev extra with the same constraint file:

```shell
python3.12 -m pip install -c constraints/python312.txt -e '.[dev]'
```

The legacy `httpx` package is intentionally absent. Current Starlette TestClient prefers `httpx2`,
which is already a runtime dependency because the installed `pvr-report` command uses TestClient.
