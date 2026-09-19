CREATE TABLE ai_calls (
    id uuid PRIMARY KEY,
    owner_id uuid REFERENCES users(id) ON DELETE SET NULL,
    operation text NOT NULL,
    request_key text NOT NULL,
    payload_hash text NOT NULL,
    model text NOT NULL,
    prompt_version text NOT NULL,
    price_snapshot jsonb NOT NULL,
    status text NOT NULL CHECK (status IN ('running','succeeded','invalid','failed','uncertain')),
    reserved_eur numeric(16,8) NOT NULL CHECK (reserved_eur >= 0),
    actual_eur numeric(16,8) CHECK (actual_eur >= 0),
    input_tokens integer,
    output_tokens integer,
    latency_ms integer,
    provider_request_id text,
    error_code text,
    result jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    UNIQUE (owner_id, operation, request_key)
);
CREATE INDEX ai_calls_month ON ai_calls(created_at);
