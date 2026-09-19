CREATE TABLE idempotency (
    owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    operation text NOT NULL,
    key text NOT NULL,
    payload_hash text NOT NULL,
    response jsonb NOT NULL,
    PRIMARY KEY(owner_id,operation,key)
);
CREATE TABLE job_keys (
    owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key text NOT NULL,
    job_id uuid NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    PRIMARY KEY(owner_id,key)
);
