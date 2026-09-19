CREATE TABLE users (
    id uuid PRIMARY KEY,
    username text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    single_user boolean NOT NULL DEFAULT true UNIQUE CHECK (single_user),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE sessions (
    token_hash text PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token text NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE login_limits (
    bucket text PRIMARY KEY,
    attempts integer NOT NULL,
    resets_at timestamptz NOT NULL
);
