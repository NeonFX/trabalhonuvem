CREATE TABLE IF NOT EXISTS sites (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    url VARCHAR(2048) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS checks (
    id BIGSERIAL PRIMARY KEY,
    site_id BIGINT NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    online BOOLEAN NOT NULL,
    status_code INTEGER,
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    error TEXT
);
CREATE INDEX IF NOT EXISTS checks_site_time_idx ON checks (site_id, checked_at DESC, id DESC);
