-- Bootstrap schema used by tools/seed.py until Alembic migrations own it (Step 4.1).
-- Same tables as Step 4.1. Vector indexes are left out: ScaNN exists only on AlloyDB,
-- and pgvector's HNSW/IVFFlat cap at 2000 dimensions (these are 3072).
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS journalists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, outlet TEXT NOT NULL,
  region TEXT, beats TEXT[] NOT NULL DEFAULT '{}', bio TEXT,
  opted_out BOOLEAN NOT NULL DEFAULT FALSE,
  profile_emb VECTOR(3072), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS journalists_beats_idx ON journalists USING gin (beats);

CREATE TABLE IF NOT EXISTS articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  journalist_id UUID NOT NULL REFERENCES journalists(id) ON DELETE CASCADE,
  title TEXT NOT NULL, url TEXT NOT NULL, published_at DATE, summary TEXT, emb VECTOR(3072)
);

CREATE TABLE IF NOT EXISTS announcements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id TEXT NOT NULL, company TEXT NOT NULL, body TEXT NOT NULL,
  verticals TEXT[] NOT NULL, emb VECTOR(3072), created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS matches (
  announcement_id UUID REFERENCES announcements(id) ON DELETE CASCADE,
  journalist_id UUID REFERENCES journalists(id) ON DELETE CASCADE,
  cosine_score REAL NOT NULL, rerank_score REAL, reason TEXT, feedback SMALLINT,
  PRIMARY KEY (announcement_id, journalist_id)
);

CREATE TABLE IF NOT EXISTS products (
  sku TEXT PRIMARY KEY, name TEXT NOT NULL, line TEXT NOT NULL,
  price_usd NUMERIC(10,2) NOT NULL, container_l NUMERIC(4,2) NOT NULL DEFAULT 2.5,
  coverage_m2_l NUMERIC(5,2), image_uri TEXT, attributes JSONB NOT NULL DEFAULT '{}'
);
