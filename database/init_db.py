"""
Database Initialization Script
Run this once to create the database with all tables and views
"""

import sqlite3
import os
import sys

def initialize_database(db_path='grading_system.db'):
    """Initialize the database with schema"""
    
    # Get paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(script_dir, 'schema.sql')
    
    # Check if schema file exists
    if not os.path.exists(schema_path):
        print(f"[ERROR] Schema file not found: {schema_path}")
        print(f"[INFO] Please create database/schema.sql first")
        return False
    
    # Check if database already exists
    if os.path.exists(db_path):
        response = input(f"[WARNING] Database already exists: {db_path}\n"
                        f"Do you want to recreate it? (yes/no): ")
        if response.lower() != 'yes':
            print("[INFO] Cancelled. Database not modified.")
            return False
        
        # Backup existing database
        backup_path = db_path.replace('.db', '_backup.db')
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"[INFO] Backed up existing database to: {backup_path}")
        except Exception as e:
            print(f"[WARNING] Could not create backup: {e}")
        
        # Remove old database
        os.remove(db_path)
        print(f"[INFO] Removed old database")
    
    # Create database
    print(f"\n[INFO] Creating database: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Read and execute schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
            cursor.executescript(schema)
        
        conn.commit()
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view';")
        views = cursor.fetchall()
        
        conn.close()
        
        print(f"\n[SUCCESS] Database initialized successfully!")
        print(f"[INFO] Location: {os.path.abspath(db_path)}")
        print(f"\n[INFO] Created {len(tables)} tables:")
        for table in tables:
            print(f"  ✓ {table[0]}")
        
        print(f"\n[INFO] Created {len(views)} views:")
        for view in views:
            print(f"  ✓ {view[0]}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"\n[ERROR] Database creation failed: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("SQLite Database Initialization")
    print("="*60)
    
    success = initialize_database()
    
    if success:
        print("\n[NEXT STEPS]")
        print("1. Open grading_system.db in DB Browser for SQLite")
        print("2. Run: python database/test_db.py")
        print("3. Integrate database into your grading flows")
    else:
        print("\n[FAILED] Database initialization did not complete")
        sys.exit(1)