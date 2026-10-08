"""
Database migration script to add boxed_image_path column
"""
import psycopg2
from backend.config import DATABASE_URL

def run_migration():
    """Add boxed_image_path column to garbage_reports table"""
    try:
        # Parse DATABASE_URL
        # Format: postgresql://user:password@host:port/database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("[MIGRATION] Checking if boxed_image_path column exists...")
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='garbage_reports' AND column_name='boxed_image_path';
        """)
        
        if cursor.fetchone():
            print("[MIGRATION] Column 'boxed_image_path' already exists. Skipping migration.")
        else:
            print("[MIGRATION] Adding boxed_image_path column...")
            cursor.execute("ALTER TABLE garbage_reports ADD COLUMN boxed_image_path TEXT;")
            conn.commit()
            print("[MIGRATION] ✓ Successfully added boxed_image_path column!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"[MIGRATION ERROR] Failed to run migration: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    run_migration()
