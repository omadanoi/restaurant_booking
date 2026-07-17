# ADR 0001: UUID primary keys, generated in Python

## Status
Accepted

## Context
Every entity needs a primary key strategy. Options considered: auto-incrementing integers, database-generated UUIDs (`gen_random_uuid()` / `uuid_generate_v4()`), or Python-generated UUIDs.

## Decision
Use UUID v4 primary keys, generated application-side via `default=uuid.uuid4` on each model's id column, stored as PostgreSQL `UUID`.

## Consequences
- No dependency on a PostgreSQL UUID-generation extension (`pgcrypto`/`uuid-ossp`) — one fewer moving part in `CREATE EXTENSION` setup, independent of the `btree_gist` extension the schema does require (see ADR 0002).
- IDs are known before `INSERT`, which simplifies constructing related objects (e.g. a reservation and its audit log entry) in a single service-layer unit of work without needing a flush to obtain a generated id first.
- IDs are not sequential/guessable, which is a reasonable default for a system exposing restaurant, reservation, and user identifiers over a public API.
- Slightly larger index size than integers; not a concern at this project's scale.
