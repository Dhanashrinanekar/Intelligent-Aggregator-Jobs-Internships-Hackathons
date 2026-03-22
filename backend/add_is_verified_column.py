"""
Add is_verified column to users table
Run this from the backend folder: python add_is_verified_column.py
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.database import engine

def add_column():
    """Add is_verified column to users table"""
    print("Adding is_verified column to users table...")
    
    with engine.connect() as connection:
        try:
            # Check if column already exists
            check_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'is_verified'
            """)
            result = connection.execute(check_sql).fetchone()
            
            if result:
                print("✅ Column 'is_verified' already exists!")
            else:
                # Add the column
                alter_sql = text("""
                    ALTER TABLE users 
                    ADD COLUMN is_verified BOOLEAN DEFAULT FALSE
                """)
                connection.execute(alter_sql)
                connection.commit()
                print("✅ Column 'is_verified' added successfully!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    add_column()
