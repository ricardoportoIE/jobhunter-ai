CREATE UNIQUE INDEX discovery_source_identity ON records(owner_id,(data->>'provider'),(data->>'reference'))
    WHERE kind='discovery_source' AND NOT deleted;
CREATE UNIQUE INDEX discovery_item_identity ON records(owner_id,(data->>'source_id'),(data->>'external_id'))
    WHERE kind='discovery_item' AND NOT deleted;
CREATE TABLE discovery_secrets (
    owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_id uuid NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    purpose text NOT NULL CHECK(purpose IN ('oauth','token')),
    ciphertext text NOT NULL,
    expires_at timestamptz,
    PRIMARY KEY(owner_id,source_id,purpose)
);
