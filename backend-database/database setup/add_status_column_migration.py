"""
Database migration to add status column to garbage_reports table
"""
import psycopg2
from backend.config import DATABASE_URL

def run_migration():
    """Add status column to garbage_reports table"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("[MIGRATION] Checking if status column exists...")
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='garbage_reports' AND column_name='status';
        """)
        
        if cursor.fetchone():
            print("[MIGRATION] Column 'status' already exists. Skipping migration.")
        else:
            print("[MIGRATION] Adding status column...")
            
            # Add status column with default value 'pending'
            cursor.execute("""
                ALTER TABLE garbage_reports 
                ADD COLUMN status VARCHAR(20) DEFAULT 'pending' NOT NULL;
            """)
            
            # Update existing records to have 'pending' status
            cursor.execute("""
                UPDATE garbage_reports 
                SET status = 'pending' 
                WHERE status IS NULL;
            """)
            
            conn.commit()
            print("[MIGRATION] ✓ Successfully added status column!")
            print("[MIGRATION] ✓ All existing reports set to 'pending' status")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"[MIGRATION ERROR] Failed to run migration: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    run_migration()
