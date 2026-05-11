-- 1. Function (Get Best Run ID for an Experiment)
CREATE OR REPLACE FUNCTION get_best_run(exp_id INT)
RETURNS INT AS $$
  SELECT id FROM runs
  WHERE experiment_id = exp_id
  ORDER BY accuracy DESC
  LIMIT 1;
$$ LANGUAGE SQL;

-- 2. Stored Procedure (Promote a Run to a Model)
CREATE OR REPLACE PROCEDURE promote_model(p_run_id INT)
LANGUAGE plpgsql AS $$
DECLARE
  v_count   INT;
  v_version VARCHAR(20);
BEGIN
  -- Generate auto-incrementing version string like v1.0, v2.0
  SELECT COUNT(*) INTO v_count FROM models;
  v_version := 'v' || (v_count + 1) || '.0';
  
  -- Insert into models and update run status
  INSERT INTO models (run_id, version, stage)
  VALUES (p_run_id, v_version, 'staging');
  
  UPDATE runs SET status = 'promoted' WHERE id = p_run_id;
END;
$$;

-- 3. View (Leaderboard query with joins)
CREATE OR REPLACE VIEW leaderboard_view AS
SELECT
  r.id,
  r.run_name,
  r.accuracy,
  r.val_loss,
  r.train_loss,
  r.status,
  r.image_url,
  r.created_at,
  e.name   AS experiment_name,
  u.name   AS scientist_name,
  u.role   AS scientist_role
FROM runs r
JOIN experiments e ON r.experiment_id = e.id
JOIN users u       ON e.user_id = u.id
ORDER BY r.accuracy DESC;

-- 4. Trigger (Flag Overfitting)
CREATE OR REPLACE FUNCTION flag_overfitting()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.val_loss IS NOT NULL AND NEW.train_loss IS NOT NULL THEN
    IF NEW.val_loss > NEW.train_loss THEN
      NEW.status := 'overfitting_alert';
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS check_overfitting ON runs;
CREATE TRIGGER check_overfitting
BEFORE INSERT OR UPDATE ON runs
FOR EACH ROW EXECUTE FUNCTION flag_overfitting();

-- 5. Indexes (for performance)
CREATE INDEX IF NOT EXISTS idx_runs_experiment_id ON runs(experiment_id);
CREATE INDEX IF NOT EXISTS idx_runs_accuracy      ON runs(accuracy DESC);
CREATE INDEX IF NOT EXISTS idx_runs_created_at    ON runs(created_at);
CREATE INDEX IF NOT EXISTS idx_metrics_run_id     ON metrics(run_id);

-- 6. Cursor (Archive stale runs over 30 days old)
CREATE OR REPLACE PROCEDURE archive_stale_runs()
LANGUAGE plpgsql AS $$
DECLARE
  cur CURSOR FOR
    SELECT id FROM runs
    WHERE status = 'completed'
    AND created_at < NOW() - INTERVAL '30 days';
  v_id INT;
BEGIN
  OPEN cur;
  LOOP
    FETCH cur INTO v_id;
    EXIT WHEN NOT FOUND;
    UPDATE runs SET status = 'archived' WHERE id = v_id;
  END LOOP;
  CLOSE cur;
END;
$$;

-- ═══════════════════════════════════════════════
-- NEW: MLOps Engineer — Deployment Feature
-- ═══════════════════════════════════════════════

-- 7. Stored Procedure: Deploy a promoted model
CREATE OR REPLACE PROCEDURE deploy_model(p_model_id INT, p_env VARCHAR(20), p_user_id INT)
LANGUAGE plpgsql AS $$
DECLARE
  v_role VARCHAR(50);
  v_stage VARCHAR(50);
BEGIN
  -- Check caller is mlops_engineer
  SELECT role INTO v_role FROM users WHERE id = p_user_id;
  IF v_role IS NULL OR v_role NOT IN ('mlops_engineer', 'admin') THEN
    RAISE EXCEPTION 'Access denied: only MLOps engineers can deploy models';
  END IF;

  -- Check model is in production-ready state
  SELECT stage INTO v_stage FROM models WHERE id = p_model_id;
  IF v_stage IS NULL THEN
    RAISE EXCEPTION 'Model % not found', p_model_id;
  END IF;

  -- Insert deployment and update model stage (transaction)
  INSERT INTO deployments (model_id, deployed_by, environment)
  VALUES (p_model_id, p_user_id, p_env);

  UPDATE models SET stage = 'deployed' WHERE id = p_model_id;
END;
$$;

-- 8. Stored Procedure: Rollback a deployment
CREATE OR REPLACE PROCEDURE rollback_deployment(p_deployment_id INT, p_reason TEXT, p_user_id INT)
LANGUAGE plpgsql AS $$
DECLARE
  v_model_id INT;
BEGIN
  -- Get model_id and mark deployment as rolled back
  SELECT model_id INTO v_model_id FROM deployments WHERE id = p_deployment_id;
  IF v_model_id IS NULL THEN
    RAISE EXCEPTION 'Deployment % not found', p_deployment_id;
  END IF;

  UPDATE deployments
  SET status = 'rolled_back', rolled_back_at = NOW()
  WHERE id = p_deployment_id;

  INSERT INTO rollback_log (deployment_id, rolled_back_by, reason)
  VALUES (p_deployment_id, p_user_id, p_reason);

  UPDATE models SET stage = 'staging' WHERE id = v_model_id;
END;
$$;

-- 9. Stored Procedure: Log health metrics for a deployment
CREATE OR REPLACE PROCEDURE log_health(
  p_deployment_id INT, p_accuracy FLOAT,
  p_latency FLOAT, p_error_rate FLOAT, p_user_id INT
)
LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO model_health_logs (deployment_id, live_accuracy, avg_latency_ms, error_rate, logged_by)
  VALUES (p_deployment_id, p_accuracy, p_latency, p_error_rate, p_user_id);
END;
$$;

-- 10. Trigger: Auto-flag degraded deployments after health log
CREATE OR REPLACE FUNCTION flag_degraded_deployment()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.live_accuracy < 0.75 OR NEW.error_rate > 0.05 THEN
    UPDATE deployments SET degraded = TRUE
    WHERE id = NEW.deployment_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS after_health_log ON model_health_logs;
CREATE TRIGGER after_health_log
AFTER INSERT ON model_health_logs
FOR EACH ROW EXECUTE FUNCTION flag_degraded_deployment();

-- 11. View: Deployment health dashboard (JOIN + subquery for latest log)
CREATE OR REPLACE VIEW deployment_health_view AS
SELECT
  d.id AS deployment_id,
  m.version AS model_name,
  d.environment,
  d.status,
  d.degraded,
  d.deployed_at,
  u.name AS deployed_by_username,
  hl.live_accuracy,
  hl.error_rate,
  hl.avg_latency_ms
FROM deployments d
JOIN models m ON d.model_id = m.id
JOIN users  u ON d.deployed_by = u.id
LEFT JOIN model_health_logs hl ON hl.id = (
  SELECT hl2.id FROM model_health_logs hl2
  WHERE hl2.deployment_id = d.id
  ORDER BY hl2.logged_at DESC LIMIT 1
);

-- 12. Function: Get deployment uptime in hours
CREATE OR REPLACE FUNCTION get_deployment_uptime(p_deployment_id INT)
RETURNS FLOAT AS $$
DECLARE
  v_status VARCHAR(20);
  v_deployed_at TIMESTAMP;
BEGIN
  SELECT status, deployed_at INTO v_status, v_deployed_at
  FROM deployments WHERE id = p_deployment_id;

  IF v_status = 'active' THEN
    RETURN EXTRACT(EPOCH FROM (NOW() - v_deployed_at)) / 3600.0;
  ELSE
    RETURN NULL;
  END IF;
END;
$$ LANGUAGE plpgsql;

-- 13. Indexes for new tables
CREATE INDEX IF NOT EXISTS idx_deployments_model_id     ON deployments(model_id);
CREATE INDEX IF NOT EXISTS idx_deployments_status       ON deployments(status);
CREATE INDEX IF NOT EXISTS idx_health_deployment_id     ON model_health_logs(deployment_id);
CREATE INDEX IF NOT EXISTS idx_health_logged_at         ON model_health_logs(logged_at);
