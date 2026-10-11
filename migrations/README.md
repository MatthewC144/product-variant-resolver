# Database Migrations

Alembic migrations define the optional PostgreSQL schema for canonical catalog retrieval, pgvector
embeddings, release staging, and Human Knowledge snapshots.

The default resolver is offline/in-memory, so these migrations are integration infrastructure—not
evidence of a live database or production deployment. Apply them only to an explicitly selected
database after reviewing `alembic.ini`, environment configuration, and the matching verification
scripts.

Tests use disposable or explicitly isolated databases. Never reset or reuse an unknown volume to
obtain a clean test environment.

