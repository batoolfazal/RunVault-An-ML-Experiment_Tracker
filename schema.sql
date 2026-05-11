-- Drop in reverse FK order
DROP TABLE IF EXISTS rollback_log CASCADE;
DROP TABLE IF EXISTS model_health_logs CASCADE;
DROP TABLE IF EXISTS deployments CASCADE;
DROP TABLE IF EXISTS models CASCADE;
DROP TABLE IF EXISTS hyperparameters CASCADE;
DROP TABLE IF EXISTS metrics CASCADE;
DROP TABLE IF EXISTS runs CASCADE;
DROP TABLE IF EXISTS experiments CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Table 1: users
CREATE TABLE users (
    id        SERIAL PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    email     VARCHAR(150) UNIQUE NOT NULL,
    password  VARCHAR(255) NOT NULL,
    role      VARCHAR(50)  NOT NULL CHECK (role IN ('data_scientist','mlops_engineer','manager','admin')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table 2: experiments
CREATE TABLE experiments (
    id          SERIAL PRIMARY KEY,
    user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Table 3: runs
CREATE TABLE runs (
    id             SERIAL PRIMARY KEY,
    experiment_id  INT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    run_name       VARCHAR(255) NOT NULL,
    accuracy       DECIMAL(5,4),
    val_loss       DECIMAL(8,6),
    train_loss     DECIMAL(8,6),
    status         VARCHAR(50) DEFAULT 'completed',
    image_url      TEXT,
    created_at     TIMESTAMP DEFAULT NOW()
);

-- Table 4: metrics
CREATE TABLE metrics (
    id           SERIAL PRIMARY KEY,
    run_id       INT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    metric_name  VARCHAR(100) NOT NULL,
    metric_value DECIMAL(8,6) NOT NULL,
    epoch        INT
);

-- Table 5: hyperparameters
CREATE TABLE hyperparameters (
    id          SERIAL PRIMARY KEY,
    run_id      INT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    param_name  VARCHAR(100) NOT NULL,
    param_value VARCHAR(100) NOT NULL
);

-- Table 6: models
CREATE TABLE models (
    id          SERIAL PRIMARY KEY,
    run_id      INT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    version     VARCHAR(20) NOT NULL,
    stage       VARCHAR(50) DEFAULT 'staging',
    promoted_at TIMESTAMP DEFAULT NOW()
);

-- Table 7: deployments (MLOps engineer feature)
CREATE TABLE deployments (
    id              SERIAL PRIMARY KEY,
    model_id        INT NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    deployed_by     INT NOT NULL REFERENCES users(id),
    environment     VARCHAR(20) NOT NULL CHECK (environment IN ('staging','production')),
    status          VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active','rolled_back','failed')),
    deployed_at     TIMESTAMP DEFAULT NOW(),
    rolled_back_at  TIMESTAMP NULL,
    degraded        BOOLEAN DEFAULT FALSE
);

-- Table 8: model_health_logs
CREATE TABLE model_health_logs (
    id              SERIAL PRIMARY KEY,
    deployment_id   INT NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    logged_at       TIMESTAMP DEFAULT NOW(),
    live_accuracy   FLOAT,
    avg_latency_ms  FLOAT,
    error_rate      FLOAT,
    logged_by       INT NOT NULL REFERENCES users(id)
);

-- Table 9: rollback_log
CREATE TABLE rollback_log (
    id              SERIAL PRIMARY KEY,
    deployment_id   INT NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    rolled_back_by  INT NOT NULL REFERENCES users(id),
    reason          TEXT,
    rolled_back_at  TIMESTAMP DEFAULT NOW()
);
