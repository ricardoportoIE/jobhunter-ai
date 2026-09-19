CREATE TABLE records (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind text NOT NULL,
    version integer NOT NULL DEFAULT 1 CHECK(version>0),
    data jsonb NOT NULL,
    deleted boolean NOT NULL DEFAULT false,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX records_owner_kind ON records(owner_id,kind);
CREATE UNIQUE INDEX one_profile ON records(owner_id) WHERE kind='profile';
CREATE TABLE snapshots (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind text NOT NULL,
    source_id uuid NOT NULL,
    version integer NOT NULL,
    data jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(owner_id,kind,source_id,version)
);
CREATE TABLE audit_events (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL,
    action text NOT NULL,
    entity_id uuid NOT NULL,
    version integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_owner_time ON audit_events(owner_id,created_at);
