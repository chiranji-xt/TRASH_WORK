"""
Database migration script to add detections column
Run this to update the existing database schema
"""
import psycopg2
import urllib.parse

# Database connection details
password = urllib.parse.quote_plus("Edi_G11$01")
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'garbage_detection_db',
    'user': 'postgres',
    'password': 'Edi_G11$01'
}

def migrate_database():
    """Add detections column to garbage_reports table"""
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='garbage_reports' AND column_name='detections';
        """)
        
        if cursor.fetchone():
            print("✓ Column 'detections' already exists. No migration needed.")
            cursor.close()
            conn.close()
            return
        
        # Add detections column
        print("Adding 'detections' column...")
        cursor.execute("""
            ALTER TABLE garbage_reports 
            ADD COLUMN detections JSONB;
        """)
        
        conn.commit()
        print("✓ Migration completed successfully!")
        print("✓ Added 'detections' column to garbage_reports table")
        
        # Verify the column was added
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='garbage_reports';
        """)
        
        print("\nCurrent table structure:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration: Add Detections Column")
    print("=" * 50)
    migrate_database()
    print("\n" + "=" * 50)
    print("Migration complete! You can now restart the server.")
    print("=" * 50)
