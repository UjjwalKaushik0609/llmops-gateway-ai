-- LLMOps Gateway AI - Database Initialization
-- This runs when PostgreSQL container starts for the first time

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Create indexes after SQLAlchemy creates tables (run by Alembic)
-- Tables are created by SQLAlchemy's init_db() call on app startup

-- Create a read-only reporting user
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'llmops_reader') THEN
        CREATE ROLE llmops_reader WITH LOGIN PASSWORD 'reader_pass_change_me';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE llmops_db TO llmops_reader;
GRANT USAGE ON SCHEMA public TO llmops_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO llmops_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO llmops_reader;
