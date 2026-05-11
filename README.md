# ML Tracker — Project README

## Overview

ML Tracker is a Flask web app for tracking machine learning experiments, logging runs, visualizing metrics, and managing simple model promotions and deployments.

## Features

- Log runs with metrics and hyperparameters
- Visualize metrics (accuracy, loss) over epochs
- Promote high-performing runs to a simple model registry
- Track deployment health logs and rollback
- Role-based access (data_scientist, mlops_engineer, manager, admin)

## Tech Stack

- Backend: Python (Flask)
- Database: PostgreSQL
- Storage: Firebase Cloud Storage (optional image uploads)
- Frontend: Jinja2 templates + Chart.js

## Quick Start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure `database.ini` with your DB and Firebase settings.

3. Initialize DB and seed data:

```bash
python setup_db.py
```

4. Run the app:

```bash
python app.py
```

Open http://127.0.0.1:5000

## Test Accounts (seeded)

- datascientist@ml.com / pass123
- mlops_engineer@ml.com / pass123
- manager@ml.com / pass123
- admin@ml.com / pass123

## Notes

- This README is intentionally concise. See source files for implementation details.
- For production, replace plaintext seed passwords with hashed passwords and secure config files.

## License

MIT

## Project made by:

Batool Binte Fazal (Reg # 2024140)
