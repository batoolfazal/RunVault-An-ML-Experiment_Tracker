import firebase_admin
from firebase_admin import credentials, storage, db
import os
import uuid
import configparser

def init_firebase():
    """
    Initializes the Firebase Admin SDK if it hasn't been initialized yet.
    """
    if not firebase_admin._apps:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(base_dir, 'database.ini')
        json_file = os.path.join(base_dir, 'firebase_config.json')
        
        config = configparser.ConfigParser()
        config.read(config_file)
        
        cred = credentials.Certificate(json_file)
        firebase_admin.initialize_app(cred, {
            'storageBucket': config.get('firebase', 'storage_bucket'),
            'databaseURL': config.get('firebase', 'database_url')
        })

def upload_file_to_firebase(file, folder='uploads'):
    """
    Uploads a file object to Firebase Cloud Storage.
    Returns the public download URL as a string.
    """
    init_firebase()
    
    # Generate unique filename
    filename = f"{folder}/{uuid.uuid4()}_{file.filename}"
    bucket = storage.bucket()
    blob = bucket.blob(filename)
    
    # Upload and make public
    blob.upload_from_file(file)
    blob.make_public()
    return blob.public_url

def save_url_to_realtime_db(run_id, image_url):
    """
    Saves Firebase Storage URL into Firebase Realtime DB
    under /runs/{run_id}/
    """
    init_firebase()
    
    ref = db.reference(f'runs/{run_id}')
    ref.set({
        'image_url': image_url
    })
