ML Tracker - Required Configuration and Run Instructions

This file lists the project-specific setup required to run the app correctly.

1) Python environment
- Recommended: Python 3.10+ (tested with Python 3.12 in this workspace)
- Install dependencies from project root:
  pip install -r requirements.txt

2) PostgreSQL configuration
- Create/update database.ini in project root with these sections:

[postgresql]
host = localhost
database = ml_tracker
user = postgres
password = YOUR_PASSWORD

[flask]
secret_key = YOUR_SECRET_KEY

[firebase]
storage_bucket = ml-tracker-a77c0.firebasestorage.app
database_url = https://ml-tracker-a77c0-default-rtdb.firebaseio.com/

Important:
- storage_bucket must use .firebasestorage.app
- Wrong DB credentials will cause startup/API failures

3) Firebase configuration
- Place Firebase service-account JSON at:
  firebase_config.json
- The service account must have access to:
  - Cloud Storage bucket configured above
  - Realtime Database URL configured above

4) Database initialization (required first run)
- From project root run:
  python setup_db.py

This sets up schema/procedures/sample data.

5) Start the app
- From project root run:
  python app.py

Open in browser:
- http://127.0.0.1:5000

6) Seed login accounts
- datascientist@ml.com / pass123
- mlops_engineer@ml.com / pass123
- manager@ml.com / pass123
- admin@ml.com / pass123

7) Role flow notes
- data_scientist logs runs
- mlops_engineer/admin promotes and deploys models

8) Images (confusion matrices)
- Local fallback path format:
  confusion_<run_name>.png
  Example: confusion_run_006.png
- Runs can also use Firebase URLs stored in PostgreSQL runs.image_url

9) Common issues
- If image clicks fail: verify app.py route /artifacts/images/<run_id> and restart app
- If registry/deploy actions fail: ensure you are logged in as mlops_engineer or admin
- If health logging fails: ensure valid numeric values (accuracy 0..1, error_rate 0..1, latency >= 0)
