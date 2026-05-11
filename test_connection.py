import configparser
import psycopg2
import firebase_admin
from firebase_admin import credentials, db
import sys
import os

def test_postgres_connection(config):
    print("\n--- Testing PostgreSQL Connection ---")
    try:
        # Read from config.ini
        host = config.get('postgresql', 'host')
        database = config.get('postgresql', 'database')
        user = config.get('postgresql', 'user')
        password = config.get('postgresql', 'password')

        print(f"Attempting to connect to host '{host}', database '{database}' as user '{user}'...")
        
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        
        # Test query
        cur = conn.cursor()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        
        print("✅ SUCCESS: Successfully connected to PostgreSQL!")
        print(f"   Database Version: {db_version[0]}")
        
        cur.close()
        conn.close()
        return True

    except configparser.NoSectionError:
        print("❌ ERROR: [postgresql] section missing in database.ini.")
    except configparser.NoOptionError as e:
        print(f"❌ ERROR: Missing option in database.ini: {e}")
    except psycopg2.OperationalError as e:
        print("❌ ERROR: Could not connect to PostgreSQL.")
        print(f"   Details: {e}")
        print("   -> Troubleshooting:")
        print("      1. Is PostgreSQL running locally (e.g. via pgAdmin)?")
        print("      2. Is the database 'ml_tracker' created?")
        print("      3. Did you replace 'your_actual_password_here' in database.ini?")
    except Exception as e:
        print(f"❌ ERROR: An unexpected error occurred: {e}")
    
    return False

def test_firebase_connection(config):
    print("\n--- Testing Firebase Realtime DB Connection ---")
    try:
        database_url = config.get('firebase', 'database_url')
        
        print(f"Checking credentials at 'firebase_config.json'...")
        if not os.path.exists('firebase_config.json'):
            print("❌ ERROR: 'firebase_config.json' file not found.")
            return False
            
        print(f"Attempting to initialize Firebase Admin SDK with URL '{database_url}'...")
        
        # Initialize the app with a service account
        if not firebase_admin._apps:
            cred = credentials.Certificate('firebase_config.json')
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            
        print("✅ SUCCESS: Firebase Admin SDK initialized.")
        
        # Try a quick read to test RTDB access
        print("Attempting to write and read a test value to Realtime DB...")
        ref = db.reference('connection_test')
        ref.set({"status": "connected", "message": "Backend to Firebase RTDB link works!"})
        
        data = ref.get()
        if data and data.get("status") == "connected":
            print("✅ SUCCESS: Successfully read/wrote to Firebase Realtime Database!")
            # Clean up test
            ref.delete()
            return True
        else:
            print("❌ ERROR: Could not read back the written test data.")
            
    except Exception as e:
        print("❌ ERROR: Firebase connection failed.")
        print(f"   Details: {e}")
        print("   -> Troubleshooting:")
        print("      1. Did you paste the actual Service Account JSON into firebase_config.json?")
        print("      2. Does the Service Account match the project at the DB URL?")
        print("      3. Note: The URL must end with '.firebaseio.com/' (no trailing extra paths).")
    
    return False

if __name__ == "__main__":
    print("=======================================")
    print("   ML Tracker - Connectivity Tester    ")
    print("=======================================")
    
    config = configparser.ConfigParser()
    config_file = 'database.ini'
    
    if not os.path.exists(config_file):
        print(f"❌ ERROR: Configuration file '{config_file}' not found.")
        print("Please ensure it exists in the same directory as this script.")
        sys.exit(1)
        
    config.read(config_file)
    
    pg_ok = test_postgres_connection(config)
    fb_ok = test_firebase_connection(config)
    
    print("\n=======================================")
    if pg_ok and fb_ok:
        print("🎉 ALL TESTS PASSED! You are ready to proceed to Phase 2.")
    else:
        print("⚠️ SOME TESTS FAILED. Please fix the errors above and re-run this script.")
    print("=======================================")
