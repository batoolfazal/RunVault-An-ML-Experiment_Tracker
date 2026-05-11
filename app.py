import os
import configparser
import json
from decimal import Decimal
from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory, send_file, abort, jsonify
from db import get_db
from firebase_helper import upload_file_to_firebase, save_url_to_realtime_db

# ── Helper: make Decimal/date JSON-safe ──
def _serialize(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

# ── Helper: Validate numeric form inputs ──
def validate_metric_input(value, field_name, min_val=None, max_val=None):
    """Validates and converts form input to float with optional range check."""
    try:
        val = float(value)
        if min_val is not None and val < min_val:
            return None, f"{field_name} must be >= {min_val}"
        if max_val is not None and val > max_val:
            return None, f"{field_name} must be <= {max_val}"
        return val, None
    except (ValueError, TypeError):
        return None, f"{field_name} must be a valid number"

def validate_int_input(value, field_name, min_val=None):
    """Validates and converts form input to integer with optional minimum check."""
    try:
        val = int(value)
        if min_val is not None and val < min_val:
            return None, f"{field_name} must be >= {min_val}"
        return val, None
    except (ValueError, TypeError):
        return None, f"{field_name} must be a valid integer"

# ============================================================================
# SECURITY NOTE (Issue #5): Password Storage
# ============================================================================
# Current implementation: Passwords stored as plaintext in PostgreSQL
# This is acceptable for TESTING/DEVELOPMENT ONLY
#
# FOR PRODUCTION, implement password hashing:
#   from werkzeug.security import generate_password_hash, check_password_hash
#
#   # When storing (e.g., in setup_db.py):
#   hashed = generate_password_hash(password, method='pbkdf2:sha256')
#   INSERT INTO users (email, password, ...) VALUES (email, hashed, ...)
#
#   # When checking (in login route below):
#   if check_password_hash(user[2], password):  # user[2] is hashed password
#       # Authentication successful
#
# Additional security recommendations for production:
# - Use HTTPS for all connections
# - Implement CSRF protection on forms
# - Add rate limiting to login endpoint
# - Enable HSTS headers
# - Store credentials securely (env vars, secrets manager)
# ============================================================================

# 1. App Config
app = Flask(__name__)

base_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(base_dir, 'database.ini')
config = configparser.ConfigParser()
config.read(config_file)

try:
    app.secret_key = config.get('flask', 'secret_key')
except configparser.NoSectionError:
    app.secret_key = 'fallback_secret_key'

# ── CORS Headers ──
@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


# ──────────────────────────────────────────────
# 2. Page Routes
# ──────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard', tab='runs'))
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Legacy routes kept for compatibility
@app.route('/home')
def home():
    return redirect(url_for('dashboard', tab='runs'))

@app.route('/leaderboard')
def leaderboard():
    return redirect(url_for('dashboard', tab='runs'))


# ── Main dashboard — single page with 4 tabs ──
@app.route('/dashboard')
@app.route('/dashboard/<tab>')
def dashboard(tab='runs'):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch experiments for the log_run form dropdown
    experiments = []
    promotable_runs = []
    with get_db() as conn:
        with conn.cursor() as cur:
            if session['user_role'] == 'data_scientist':
                cur.execute("SELECT id, name FROM experiments WHERE user_id = %s", (session['user_id'],))
                experiments = cur.fetchall()
            if session['user_role'] in ['mlops_engineer', 'admin']:
                cur.execute("""
                    SELECT r.id, r.run_name, r.accuracy, e.name
                    FROM runs r
                    JOIN experiments e ON r.experiment_id = e.id
                    WHERE r.status = 'completed'
                """)
                promotable_runs = cur.fetchall()

    return render_template('dashboard.html',
                           active_tab=tab,
                           experiments=experiments,
                           promotable_runs=promotable_runs)


# ──────────────────────────────────────────────
# 3. API Routes (JSON)
# ──────────────────────────────────────────────

@app.route('/api/runs/all')
def api_runs_all():
    """All runs with metadata for the sidebar and charts."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT r.id, r.run_name, r.accuracy, r.val_loss, r.train_loss,
                           r.status, r.image_url, r.created_at,
                           e.name AS experiment_name,
                           u.name AS scientist_name
                    FROM runs r
                    JOIN experiments e ON r.experiment_id = e.id
                    JOIN users u ON e.user_id = u.id
                    ORDER BY r.id ASC
                """)
                columns = [d[0] for d in cur.description]
                rows = cur.fetchall()

                # Fetch hyperparameters for each run
                runs = []
                for row in rows:
                    run = dict(zip(columns, row))
                    cur.execute("""
                        SELECT param_name, param_value FROM hyperparameters WHERE run_id = %s
                    """, (run['id'],))
                    params = {r[0]: r[1] for r in cur.fetchall()}
                    run['hyperparameters'] = params
                    runs.append(run)

        return jsonify({"success": True, "data": runs}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/runs/<int:run_id>/metrics')
def api_run_metrics(run_id):
    """Metrics for a single run, grouped by metric_name, sorted by epoch."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT metric_name, metric_value, epoch
                    FROM metrics WHERE run_id = %s ORDER BY epoch
                """, (run_id,))
                rows = cur.fetchall()

        # Group by metric_name
        grouped = {}
        for name, value, epoch in rows:
            grouped.setdefault(name, []).append({"epoch": epoch, "value": float(value)})

        return jsonify({"success": True, "data": grouped}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/metrics/all')
def api_metrics_all():
    """All metrics for all runs, for the Metrics tab charts."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT r.id, r.run_name, m.metric_name, m.metric_value, m.epoch
                    FROM metrics m
                    JOIN runs r ON m.run_id = r.id
                    ORDER BY r.id, m.metric_name, m.epoch
                """)
                rows = cur.fetchall()

        # Structure: {run_id: {run_name, metrics: {metric_name: [{epoch, value}]}}}
        data = {}
        for run_id, run_name, metric_name, value, epoch in rows:
            if run_id not in data:
                data[run_id] = {"run_name": run_name, "metrics": {}}
            data[run_id]["metrics"].setdefault(metric_name, []).append({
                "epoch": epoch, "value": float(value)
            })

        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/deployments/all')
def api_deployments_all():
    """All deployments from the deployment_health_view + uptime."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM deployment_health_view")
                columns = [d[0] for d in cur.description]
                rows = cur.fetchall()

                deployments = []
                for row in rows:
                    dep = dict(zip(columns, row))
                    # Get uptime
                    cur.execute("SELECT get_deployment_uptime(%s)", (dep['deployment_id'],))
                    uptime = cur.fetchone()[0]
                    dep['uptime_hours'] = round(float(uptime), 1) if uptime is not None else None
                    deployments.append(dep)

        return jsonify({"success": True, "data": deployments}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/models')
def api_models_all():
    """List promoted/registered models with run and experiment metadata."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT m.id, m.run_id, m.version, m.stage, m.promoted_at,
                           r.run_name, r.accuracy, e.name AS experiment_name, u.name AS scientist_name
                    FROM models m
                    JOIN runs r ON m.run_id = r.id
                    JOIN experiments e ON r.experiment_id = e.id
                    JOIN users u ON e.user_id = u.id
                    ORDER BY m.promoted_at DESC
                """)
                columns = [d[0] for d in cur.description]
                rows = cur.fetchall()

                models = []
                for row in rows:
                    models.append(dict(zip(columns, row)))

        return jsonify({"success": True, "data": models}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/models/<int:model_id>/deploy', methods=['POST'])
def api_deploy_model(model_id):
    """Deploy a staged model to staging/production (MLOps/Admin only)."""
    if 'user_id' not in session or session['user_role'] not in ['mlops_engineer', 'admin']:
        return jsonify({"success": False, "error": "Access denied"}), 403

    data = request.get_json() or request.form
    environment = (data.get('environment') or 'staging').strip().lower()
    if environment not in ['staging', 'production']:
        return jsonify({"success": False, "error": "Invalid environment"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("CALL deploy_model(%s, %s, %s)",
                            (model_id, environment, session['user_id']))
                conn.commit()

        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/deployments/<int:dep_id>/log_health', methods=['POST'])
def api_log_health(dep_id):
    """Log health metrics for a deployment."""
    if 'user_id' not in session or session['user_role'] not in ['mlops_engineer', 'admin']:
        return jsonify({"success": False, "error": "Access denied"}), 403

    data = request.get_json() or request.form
    try:
        live_accuracy_raw = data.get('live_accuracy') if data else None
        latency_raw = data.get('avg_latency_ms') if data else None
        error_rate_raw = data.get('error_rate') if data else None

        if live_accuracy_raw in [None, ''] or latency_raw in [None, ''] or error_rate_raw in [None, '']:
            return jsonify({
                "success": False,
                "error": "All fields are required: live_accuracy, avg_latency_ms, error_rate"
            }), 400

        accuracy = float(live_accuracy_raw)
        latency = float(latency_raw)
        error_rate = float(error_rate_raw)

        if not (0 <= accuracy <= 1):
            return jsonify({"success": False, "error": "live_accuracy must be between 0 and 1"}), 400
        if latency < 0:
            return jsonify({"success": False, "error": "avg_latency_ms must be >= 0"}), 400
        if not (0 <= error_rate <= 1):
            return jsonify({"success": False, "error": "error_rate must be between 0 and 1"}), 400

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM deployments WHERE id = %s", (dep_id,))
                if cur.fetchone() is None:
                    return jsonify({"success": False, "error": f"Deployment {dep_id} not found"}), 404

                cur.execute("CALL log_health(%s, %s, %s, %s, %s)",
                            (dep_id, accuracy, latency, error_rate, session['user_id']))
                conn.commit()

        return jsonify({"success": True}), 200
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid numeric input for health metrics"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/deployments/<int:dep_id>/rollback', methods=['POST'])
def api_rollback(dep_id):
    """Rollback a deployment."""
    if 'user_id' not in session or session['user_role'] not in ['mlops_engineer', 'admin']:
        return jsonify({"success": False, "error": "Access denied"}), 403

    data = request.get_json() or request.form
    reason = data.get('reason', 'No reason provided')

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("CALL rollback_deployment(%s, %s, %s)",
                            (dep_id, reason, session['user_id']))
                conn.commit()

        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ──────────────────────────────────────────────
# 4. Existing Feature Routes (kept for compatibility)
# ──────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User authentication with session-based login.
    
    SECURITY NOTE: Currently compares plaintext passwords.
    In production, use werkzeug.security.check_password_hash() instead.
    """
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with get_db() as conn:
            with conn.cursor() as cur:
                # NOTE: For production, fetch hashed password and use check_password_hash()
                cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
                user = cur.fetchone()

        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_role'] = user[4]
            return redirect(url_for('dashboard', tab='runs'))
        else:
            flash("Invalid credentials, please try again.")

    return render_template('login.html')


@app.route('/log_run', methods=['GET', 'POST'])
def log_run():
    if 'user_id' not in session or session['user_role'] != 'data_scientist':
        return redirect(url_for('dashboard', tab='runs'))

    if request.method == 'POST':
        experiment_id = request.form.get('experiment_id', '').strip()
        run_name = request.form.get('run_name', '').strip()

        if not experiment_id:
            flash("Experiment is required")
            return redirect(url_for('log_run'))

        if not run_name:
            flash("Run Name is required")
            return redirect(url_for('log_run'))

        accuracy, err = validate_metric_input(request.form.get('accuracy'), 'Accuracy', 0, 1)
        if err:
            flash(err)
            return redirect(url_for('log_run'))

        val_loss, err = validate_metric_input(request.form.get('val_loss'), 'Validation Loss', 0)
        if err:
            flash(err)
            return redirect(url_for('log_run'))

        train_loss, err = validate_metric_input(request.form.get('train_loss'), 'Training Loss', 0)
        if err:
            flash(err)
            return redirect(url_for('log_run'))

        f1_score, err = validate_metric_input(request.form.get('f1_score'), 'F1 Score', 0, 1)
        if err:
            flash(err)
            return redirect(url_for('log_run'))

        epochs, err = validate_int_input(request.form.get('epochs'), 'Epochs', 1)
        if err:
            flash(err)
            return redirect(url_for('log_run'))

        learning_rate = request.form.get('learning_rate', '').strip()
        if not learning_rate:
            flash("Learning Rate is required")
            return redirect(url_for('log_run'))

        gpu_count, err = validate_int_input(request.form.get('gpu_count'), 'GPU Count', 0)
        if err:
            flash(err)
            return redirect(url_for('log_run'))

        image_file = request.files.get('image')
        image_url = None
        if image_file and image_file.filename:
            image_url = upload_file_to_firebase(image_file, folder='images')

        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO runs (experiment_id, run_name, accuracy, val_loss, train_loss, image_url)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """, (experiment_id, run_name, accuracy, val_loss, train_loss, image_url))
                    run_id = cur.fetchone()[0]

                    # Insert per-epoch metric series so charts render full lines, not a single point.
                    metric_rows = []
                    for epoch in range(1, epochs + 1):
                        progress = epoch / float(epochs)
                        acc_epoch = max(0.0, min(1.0, accuracy * progress))
                        f1_epoch = max(0.0, min(1.0, f1_score * progress))
                        # Loss starts higher and trends down to train_loss.
                        loss_epoch = train_loss + (train_loss * (1.0 - progress))
                        # Keep val_accuracy slightly below accuracy curve.
                        val_acc_epoch = max(0.0, min(1.0, acc_epoch * 0.99))

                        metric_rows.extend([
                            (run_id, 'accuracy', acc_epoch, epoch),
                            (run_id, 'loss', loss_epoch, epoch),
                            (run_id, 'val_accuracy', val_acc_epoch, epoch),
                            (run_id, 'f1_score', f1_epoch, epoch),
                        ])

                    cur.executemany(
                        "INSERT INTO metrics (run_id, metric_name, metric_value, epoch) VALUES (%s, %s, %s, %s)",
                        metric_rows,
                    )

                    # Insert hyperparameters used in run details + GPU chart.
                    hyper_rows = [
                        (run_id, 'learning_rate', learning_rate),
                        (run_id, 'epochs', str(epochs)),
                        (run_id, 'gpu_count', str(gpu_count)),
                    ]
                    cur.executemany(
                        "INSERT INTO hyperparameters (run_id, param_name, param_value) VALUES (%s, %s, %s)",
                        hyper_rows,
                    )

                    conn.commit()

            save_url_to_realtime_db(run_id, image_url)
            flash("Run logged successfully!")
            return redirect(url_for('dashboard', tab='runs'))

        except Exception as e:
            print(f"Transaction failed: {e}")
            flash(f"Error logging run: {str(e)[:100]}")
            return redirect(url_for('log_run'))

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM experiments WHERE user_id = %s", (session['user_id'],))
            experiments = cur.fetchall()

    return render_template('log_run.html', experiments=experiments)


@app.route('/promote/<int:run_id>', methods=['POST'])
def promote(run_id):
    if 'user_id' not in session or session['user_role'] not in ['mlops_engineer', 'admin']:
        return redirect(url_for('dashboard', tab='registry'))

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("CALL promote_model(%s)", (run_id,))
                conn.commit()
        flash(f"Run {run_id} promoted to model successfully!")
    except Exception as e:
        flash(f"Failed to promote model: {e}")

    return redirect(url_for('dashboard', tab='registry'))


@app.route('/artifacts/images/<int:run_id>')
def run_image(run_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT run_name, image_url FROM runs WHERE id = %s", (run_id,))
            row = cur.fetchone()

    if not row:
        abort(404)

    run_name, image_url = row
    image_name = f"confusion_{run_name}.png"
    image_path = os.path.join(base_dir, image_name)

    if not os.path.exists(image_path):
        if image_url and image_url.startswith('http'):
            try:
                from io import BytesIO
                from urllib.request import urlopen

                with urlopen(image_url) as response:
                    content = response.read()
                    mime_type = response.headers.get_content_type() or 'image/png'
                return send_file(BytesIO(content), mimetype=mime_type, as_attachment=False, download_name=image_name)
            except Exception:
                abort(404)
        abort(404)

    return send_file(image_path, mimetype='image/png', as_attachment=False, download_name=image_name)


# ── JSON encoder for Decimal ──
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)

app.json_encoder = DecimalEncoder


if __name__ == '__main__':
    app.run(debug=True)
