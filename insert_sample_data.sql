-- Clear existing data first
TRUNCATE TABLE rollback_log, model_health_logs, deployments, models, hyperparameters, metrics, runs, experiments, users RESTART IDENTITY CASCADE;

-- 4 Users: Data Scientist, MLOps Engineer, Manager, Admin
INSERT INTO users (name, email, password, role) VALUES
('Data Scientist',  'datascientist@ml.com',  'pass123', 'data_scientist'),
('MLOps Engineer',  'mlops_engineer@ml.com', 'pass123', 'mlops_engineer'),
('Manager',         'manager@ml.com',        'pass123', 'manager'),
('Admin',           'admin@ml.com',          'pass123', 'admin');

-- Experiments
INSERT INTO experiments (user_id, name, description) VALUES
(1, 'Image Classification v1', 'Classifying cats vs dogs'),
(1, 'Speech Recognition v1',   'Urdu speech to text');

-- Runs (W&B-inspired names and varied metrics for chart data)
INSERT INTO runs (experiment_id, run_name, accuracy, val_loss, train_loss, image_url) VALUES
(1, 'run_001', 0.9134, 0.2100, 0.1800, NULL),
(1, 'run_002', 0.8721, 0.3200, 0.2100, NULL),
(1, 'run_003', 0.9450, 0.1800, 0.1500, NULL),
(2, 'run_004', 0.8200, 0.4100, 0.3800, NULL),
(2, 'run_005', 0.7600, 0.5500, 0.4900, NULL);

-- Metrics: multiple epochs per run for chart line data
INSERT INTO metrics (run_id, metric_name, metric_value, epoch) VALUES
-- run_001 accuracy over epochs
(1, 'accuracy',      0.5200, 1),
(1, 'accuracy',      0.6800, 3),
(1, 'accuracy',      0.7900, 5),
(1, 'accuracy',      0.8500, 7),
(1, 'accuracy',      0.9134, 10),
-- run_001 loss over epochs
(1, 'loss',          1.4200, 1),
(1, 'loss',          0.9100, 3),
(1, 'loss',          0.5400, 5),
(1, 'loss',          0.3200, 7),
(1, 'loss',          0.2100, 10),
-- run_001 val_accuracy
(1, 'val_accuracy',  0.4800, 1),
(1, 'val_accuracy',  0.6200, 3),
(1, 'val_accuracy',  0.7500, 5),
(1, 'val_accuracy',  0.8100, 7),
(1, 'val_accuracy',  0.8900, 10),
-- run_001 other metrics
(1, 'f1_score',  0.9012, 10),
(1, 'precision', 0.9200, 10),
(1, 'recall',    0.8900, 10),

-- run_002 accuracy over epochs
(2, 'accuracy',      0.4500, 1),
(2, 'accuracy',      0.6100, 3),
(2, 'accuracy',      0.7200, 5),
(2, 'accuracy',      0.8100, 7),
(2, 'accuracy',      0.8721, 10),
-- run_002 loss
(2, 'loss',          1.6800, 1),
(2, 'loss',          1.1200, 3),
(2, 'loss',          0.7400, 5),
(2, 'loss',          0.4600, 7),
(2, 'loss',          0.3200, 10),
-- run_002 val_accuracy
(2, 'val_accuracy',  0.4100, 1),
(2, 'val_accuracy',  0.5500, 3),
(2, 'val_accuracy',  0.6800, 5),
(2, 'val_accuracy',  0.7600, 7),
(2, 'val_accuracy',  0.8400, 10),
(2, 'f1_score',  0.8600, 10),

-- run_003 accuracy over epochs
(3, 'accuracy',      0.5800, 1),
(3, 'accuracy',      0.7200, 5),
(3, 'accuracy',      0.8400, 10),
(3, 'accuracy',      0.9100, 15),
(3, 'accuracy',      0.9450, 20),
-- run_003 loss
(3, 'loss',          1.3100, 1),
(3, 'loss',          0.7200, 5),
(3, 'loss',          0.3800, 10),
(3, 'loss',          0.2200, 15),
(3, 'loss',          0.1800, 20),
-- run_003 val_accuracy
(3, 'val_accuracy',  0.5200, 1),
(3, 'val_accuracy',  0.6700, 5),
(3, 'val_accuracy',  0.8000, 10),
(3, 'val_accuracy',  0.8700, 15),
(3, 'val_accuracy',  0.9200, 20),
(3, 'f1_score',  0.9310, 10),
(3, 'precision', 0.9400, 10),

-- run_004 accuracy over epochs
(4, 'accuracy',      0.3800, 1),
(4, 'accuracy',      0.5500, 5),
(4, 'accuracy',      0.7000, 10),
(4, 'accuracy',      0.7800, 15),
(4, 'accuracy',      0.8200, 20),
-- run_004 loss
(4, 'loss',          1.7600, 1),
(4, 'loss',          1.2000, 5),
(4, 'loss',          0.7100, 10),
(4, 'loss',          0.4800, 15),
(4, 'loss',          0.4100, 20),

-- run_005 accuracy over epochs
(5, 'accuracy',      0.3200, 1),
(5, 'accuracy',      0.4800, 5),
(5, 'accuracy',      0.6200, 10),
(5, 'accuracy',      0.7100, 15),
(5, 'accuracy',      0.7600, 20),
-- run_005 loss
(5, 'loss',          1.8500, 1),
(5, 'loss',          1.3200, 5),
(5, 'loss',          0.8800, 10),
(5, 'loss',          0.6200, 15),
(5, 'loss',          0.5500, 20);

-- Hyperparameters
INSERT INTO hyperparameters (run_id, param_name, param_value) VALUES
(1, 'learning_rate', '0.001'),
(1, 'batch_size',    '32'),
(1, 'epochs',        '10'),
(1, 'optimizer',     'adam'),
(1, 'gpu_count',     '1'),
(2, 'learning_rate', '0.01'),
(2, 'batch_size',    '64'),
(2, 'epochs',        '10'),
(2, 'optimizer',     'rmsprop'),
(2, 'gpu_count',     '4'),
(3, 'learning_rate', '0.0001'),
(3, 'batch_size',    '64'),
(3, 'epochs',        '20'),
(3, 'optimizer',     'adam'),
(3, 'gpu_count',     '4'),
(4, 'learning_rate', '0.005'),
(4, 'batch_size',    '128'),
(4, 'epochs',        '20'),
(4, 'optimizer',     'adam'),
(4, 'gpu_count',     '2'),
(5, 'learning_rate', '0.01'),
(5, 'batch_size',    '256'),
(5, 'epochs',        '20'),
(5, 'optimizer',     'rmsprop'),
(5, 'gpu_count',     '1');

-- Promote runs 1 and 3 into models (so we can deploy them)
-- Using direct INSERT instead of CALL to avoid trigger side effects on status
INSERT INTO models (run_id, version, stage) VALUES
(1, 'v1.0', 'staging'),
(3, 'v2.0', 'staging');

-- Deployments: 3 total (deployed_by = 2 = MLOps Engineer)
INSERT INTO deployments (model_id, deployed_by, environment, status, degraded) VALUES
(1, 2, 'production', 'active',      FALSE),   -- deployment 1: healthy
(2, 2, 'staging',    'active',      FALSE),   -- deployment 2: will become degraded
(1, 2, 'staging',    'rolled_back', FALSE);   -- deployment 3: already rolled back

-- Update rolled_back deployment timestamp
UPDATE deployments SET rolled_back_at = NOW() - INTERVAL '2 days' WHERE id = 3;

-- Health logs: trigger will auto-set degraded=TRUE for deployment 2
INSERT INTO model_health_logs (deployment_id, live_accuracy, avg_latency_ms, error_rate, logged_by) VALUES
(1, 0.92, 45.2,  0.01, 2),   -- healthy
(1, 0.91, 48.1,  0.02, 2),   -- healthy
(2, 0.80, 52.0,  0.03, 2),   -- ok initially
(2, 0.40, 120.5, 0.08, 2);   -- BAD: triggers degraded=TRUE

-- Rollback log for deployment 3
INSERT INTO rollback_log (deployment_id, rolled_back_by, reason) VALUES
(3, 2, 'Accuracy dropped below threshold in staging environment');
