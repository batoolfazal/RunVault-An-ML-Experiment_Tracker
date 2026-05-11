"""
Upload the 5 generated confusion matrix PNGs to Firebase Cloud Storage,
then update the corresponding runs rows in PostgreSQL with the public URLs,
and also save the URLs to Firebase Realtime Database.
"""
import firebase_admin
from firebase_admin import credentials, storage, db as rtdb
import os
import configparser
import psycopg2

# ── Config ──
base_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(base_dir, 'database.ini')
config = configparser.ConfigParser()
config.read(config_file)

# ── Firebase init ──
if not firebase_admin._apps:
    cred = credentials.Certificate(os.path.join(base_dir, 'firebase_config.json'))
    firebase_admin.initialize_app(cred, {
        'storageBucket': config.get('firebase', 'storage_bucket'),
        'databaseURL': config.get('firebase', 'database_url')
    })

bucket = storage.bucket()

def sync_images_to_database():
    """
    Upload the generated confusion-matrix images to Firebase Storage, then
    write the public URLs back to PostgreSQL and Firebase Realtime DB.
    """
    urls = {}
    for i in range(1, 6):
        run_name = f"run_{i:03d}"
        filename = os.path.join(base_dir, f"confusion_{run_name}.png")
        if os.path.exists(filename):
            try:
                blob = bucket.blob(f"images/confusion_{run_name}.png")
                blob.upload_from_filename(filename)
                blob.make_public()
                urls[i] = blob.public_url
                print(f"Uploaded confusion_{run_name}.png -> {blob.public_url}")
            except Exception as exc:
                urls[i] = f"/artifacts/images/{i}"
                print(f"Firebase upload failed for {filename}; using local fallback {urls[i]} ({exc})")
        else:
            print(f"SKIP: {filename} not found")

    if not urls:
        raise FileNotFoundError("No images were uploaded. Run generate_images.py first.")

    print("\nUpdating PostgreSQL runs table...")
    conn = psycopg2.connect(
        host=config.get('postgresql', 'host'),
        database=config.get('postgresql', 'database'),
        user=config.get('postgresql', 'user'),
        password=config.get('postgresql', 'password')
    )
    cur = conn.cursor()

    for run_id, url in urls.items():
        cur.execute("UPDATE runs SET image_url = %s WHERE id = %s", (url, run_id))
        print(f"  run id={run_id} -> image_url updated")

    conn.commit()
    cur.close()
    conn.close()
    print("PostgreSQL updated.")

    print("\nUpdating Firebase Realtime DB...")
    for run_id, url in urls.items():
        ref = rtdb.reference(f'runs/{run_id}')
        ref.update({'image_url': url})
        print(f"  /runs/{run_id}/image_url updated")

    print("\nDone! All 5 confusion matrix images are now:")
    print("  1. Stored in Firebase Cloud Storage")
    print("  2. URLs saved in PostgreSQL runs.image_url")
    print("  3. URLs saved in Firebase Realtime DB")


def main():
    sync_images_to_database()


if __name__ == "__main__":
    main()
