import sqlite3
import os
import sys

# Add project root to path to allow imports if needed, though we'll try to keep this script self-contained
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

# Paths
DB_DIR = os.path.join(project_root, 'app', 'data', 'dao', 'storage')
OLD_DB_PATH = os.path.join(DB_DIR, 'focus_app.db')
PERIOD_STATS_DB_PATH = os.path.join(DB_DIR, 'period_stats.db')
CORE_EVENTS_DB_PATH = os.path.join(DB_DIR, 'core_events.db')

def get_schema(table_name):
    """Get the CREATE TABLE statement from the old database."""
    conn = sqlite3.connect(OLD_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    return None

def migrate_table(table_name, new_db_path):
    print(f"Migrating {table_name} to {new_db_path}...")
    
    if not os.path.exists(OLD_DB_PATH):
        print(f"Error: {OLD_DB_PATH} does not exist.")
        return

    # Check if table exists in old DB
    schema = get_schema(table_name)
    if not schema:
        print(f"Table {table_name} not found in old database. Skipping.")
        # If table doesn't exist in old DB, we still might want to create the new DB with empty table
        # But for migration, we skip data copy.
        # We will initialize the new DB with schema anyway.
        return

    # Connect to new DB
    conn_new = sqlite3.connect(new_db_path)
    cursor_new = conn_new.cursor()
    
    # Create table in new DB
    # We might need to adjust the schema if it refers to other tables, but these tables seem independent.
    try:
        cursor_new.execute(schema)
    except sqlite3.OperationalError as e:
        print(f"Error creating table {table_name}: {e}")
    
    # Attach old DB to copy data
    # Windows path might need escaping or raw string? sqlite3 usually handles paths well.
    # But safer to pass as parameter if possible, but ATTACH syntax is specific.
    # We'll use f-string with replacement for backslashes just in case.
    old_db_path_fixed = OLD_DB_PATH.replace('\\', '/')
    cursor_new.execute(f"ATTACH DATABASE '{old_db_path_fixed}' AS old_db")
    
    # Copy data
    try:
        print(f"Copying data for {table_name}...")
        cursor_new.execute(f"INSERT INTO main.{table_name} SELECT * FROM old_db.{table_name}")
        conn_new.commit()
        print(f"Successfully migrated {table_name}.")
    except sqlite3.Error as e:
        print(f"Error copying data: {e}")
    
    # Detach
    cursor_new.execute("DETACH DATABASE old_db")
    conn_new.close()
    
    # Drop table from old DB
    # We'll do this in a separate connection to old DB to be safe
    try:
        conn_old = sqlite3.connect(OLD_DB_PATH)
        conn_old.execute(f"DROP TABLE {table_name}")
        conn_old.commit()
        conn_old.close()
        print(f"Dropped {table_name} from old database.")
    except sqlite3.Error as e:
        print(f"Error dropping table from old DB: {e}")

def main():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    # Migrate Period Stats
    migrate_table('period_stats', PERIOD_STATS_DB_PATH)
    
    # Migrate Core Events
    migrate_table('core_events', CORE_EVENTS_DB_PATH)
    
    print("Migration completed.")

if __name__ == "__main__":
    main()
