-- Runs once, at container init, against the default (POSTGRES_DB) database.
-- Enables the extension the reservation overlap constraint depends on (ADR 0002),
-- and creates a second database for the test suite so tests never touch dev data.

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE DATABASE restaurant_platform_test;

\connect restaurant_platform_test

CREATE EXTENSION IF NOT EXISTS btree_gist;
