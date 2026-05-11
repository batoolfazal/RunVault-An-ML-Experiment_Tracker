import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

from upload_images import sync_images_to_database

base_dir = os.path.dirname(os.path.abspath(__file__))

print("Connecting to postgres to create ml_tracker DB...")
# 1. Create database
try:
    conn = psycopg2.connect(host='localhost', database='postgres', user='postgres', password='batool123')
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute('CREATE DATABASE ml_tracker;')
    cur.close()
    conn.close()
    print("✅ Database ml_tracker created successfully.")
except psycopg2.errors.DuplicateDatabase:
    print("✅ Database ml_tracker already exists.")
except Exception as e:
    print(f"❌ Error creating DB: {e}")

# 2. Run SQL files
print("Connecting to ml_tracker to execute SQL scripts...")
try:
    conn = psycopg2.connect(host='localhost', database='ml_tracker', user='postgres', password='batool123')
    cur = conn.cursor()
    
    with open(os.path.join(base_dir, 'schema.sql'), 'r', encoding='utf-8') as f:
        cur.execute(f.read())
    print("✅ schema.sql executed.")
    
    with open(os.path.join(base_dir, 'procedures.sql'), 'r', encoding='utf-8') as f:
        cur.execute(f.read())
    print("✅ procedures.sql executed.")
    
    with open(os.path.join(base_dir, 'insert_sample_data.sql'), 'r', encoding='utf-8') as f:
        cur.execute(f.read())
    print("✅ insert_sample_data.sql executed.")
    
    conn.commit()
    cur.close()
    conn.close()
    print("🎉 All SQL scripts executed successfully!")

    print("\nSyncing confusion matrix images to Firebase and PostgreSQL...")
    sync_images_to_database()
    print("✅ Image URLs synchronized.")
except Exception as e:
    print(f"❌ Error executing scripts: {e}")
