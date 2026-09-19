CREATE TABLE ai_embeddings (
    owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('job','fact')),
    source_id uuid NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    source_version integer NOT NULL,
    model text NOT NULL,
    chunk integer NOT NULL,
    vector double precision[] NOT NULL CHECK (array_length(vector,1)=256),
    run_id uuid NOT NULL REFERENCES ai_calls(id),
    PRIMARY KEY(owner_id,kind,source_id,source_version,model,chunk)
);
