CREATE TABLE IF NOT EXISTS valid_services (
    id           SERIAL PRIMARY KEY,
    service_name VARCHAR(255) UNIQUE NOT NULL,
    team_owner   VARCHAR(255) NOT NULL,
    tier         VARCHAR(50)  NOT NULL DEFAULT 'standard'
);

INSERT INTO valid_services (service_name, team_owner, tier) VALUES
    ('user-billing-db',  'payments-team', 'critical'),
    ('auth-service',     'identity-team', 'critical'),
    ('checkout-api',     'commerce-team', 'critical'),
    ('notification-svc', 'comms-team',    'standard'),
    ('image-resizer',    'media-team',    'standard')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS triage_log (
    id                SERIAL PRIMARY KEY,
    raw_input         TEXT NOT NULL,
    service_name      VARCHAR(255),
    severity_level    VARCHAR(50),
    is_db_issue       BOOLEAN,
    trust_score       FLOAT,
    langfuse_trace_id VARCHAR(255),
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
