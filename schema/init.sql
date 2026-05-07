-- Traceset Alpha: Full DDL
-- Apply to Supabase with: psql $SUPABASE_DB_URL -f schema/init.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Entity tables ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS commits (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_full_name   TEXT        NOT NULL,
    sha              TEXT        NOT NULL UNIQUE,
    author           TEXT,
    message          TEXT,
    keywords_matched TEXT[],
    raw_diff         TEXT,
    committed_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS papers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    arxiv_id            TEXT UNIQUE,
    semantic_scholar_id TEXT UNIQUE,
    title               TEXT        NOT NULL,
    abstract            TEXT,
    authors             TEXT[],
    published_at        DATE,
    url                 TEXT,
    categories          TEXT[],
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patents (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patent_number TEXT UNIQUE,
    title         TEXT        NOT NULL,
    abstract      TEXT,
    assignee      TEXT,
    inventors     TEXT[],
    filing_date   DATE,
    grant_date    DATE,
    cpc_class     TEXT,
    source        TEXT        NOT NULL CHECK (source IN ('USPTO', 'WIPO')),
    url           TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Trace (join) table ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS traces (
    id               UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
    commit_id        UUID  REFERENCES commits(id) ON DELETE SET NULL,
    paper_id         UUID  REFERENCES papers(id)  ON DELETE SET NULL,
    patent_id        UUID  REFERENCES patents(id) ON DELETE SET NULL,
    trace_type       TEXT  NOT NULL
        CHECK (trace_type IN ('commit_paper', 'commit_patent', 'paper_patent', 'trilinear')),
    confidence_score FLOAT NOT NULL CHECK (confidence_score BETWEEN 0.0 AND 1.0),
    reasoning        TEXT  NOT NULL,
    model_version    TEXT  NOT NULL,
    prompt_version   INT   NOT NULL DEFAULT 1,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT at_least_two_artifacts CHECK (
        (commit_id IS NOT NULL)::INT +
        (paper_id  IS NOT NULL)::INT +
        (patent_id IS NOT NULL)::INT >= 2
    )
);

CREATE INDEX IF NOT EXISTS idx_traces_confidence ON traces (confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_traces_commit     ON traces (commit_id);
CREATE INDEX IF NOT EXISTS idx_traces_paper      ON traces (paper_id);
CREATE INDEX IF NOT EXISTS idx_traces_patent     ON traces (patent_id);
CREATE INDEX IF NOT EXISTS idx_traces_created    ON traces (created_at DESC);
