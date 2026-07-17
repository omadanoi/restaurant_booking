# ADR 0002: PostgreSQL EXCLUDE constraint as the source of truth for double-booking prevention

## Status
Accepted

## Context
The system must guarantee that two overlapping, active reservations can never exist for the same table, even under concurrent requests. Pure application-level solutions (e.g. only using `SELECT ... FOR UPDATE` plus an overlap query before insert) are only as strong as every code path that remembers to use them correctly — a bulk import script, an admin tool, or a future feature added under time pressure could bypass the check.

## Decision
Enforce the invariant at the database level with a PostgreSQL `EXCLUDE` constraint using the `btree_gist` extension:

```sql
EXCLUDE USING gist (
  table_id WITH =,
  tstzrange(start_time, end_time, '[)') WITH &&
) WHERE (status NOT IN ('cancelled', 'no_show'))
```

This makes overlapping active reservations for the same table structurally impossible at the schema level.

The service layer additionally takes a row lock (`SELECT ... FOR UPDATE`) on the target table and performs an explicit overlap check inside the same transaction before attempting the insert. This is not redundant: it lets well-behaved callers fail fast with a clean domain error (`OverlappingReservationError` -> HTTP 409) instead of surfacing a raw `ExclusionViolation`/`IntegrityError`. The constraint remains the backstop of record.

## Consequences
- Requires `CREATE EXTENSION IF NOT EXISTS btree_gist;`, applied in the first Alembic migration.
- SQLite cannot be used for any test that touches reservations (no GiST/EXCLUDE/`tstzrange` support), so the test suite runs against a real PostgreSQL database for the life of the project.
- Any future write path to `reservations` — including manual data fixes — is automatically protected without needing to remember to re-implement the locking logic.
- Concurrency correctness is testable at two levels: a raw-SQL test against the constraint directly (no service code required), and a concurrent-request integration test against the running API.
