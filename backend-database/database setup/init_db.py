"""
Database initialization script
Run this to create all tables in the database
"""
from backend.db import engine, Base
from backend.models import GarbageReport

def init_db():
    """Create all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully!")

if __name__ == "__main__":
    init_db()
