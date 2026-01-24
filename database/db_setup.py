import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.models import init_db

if __name__ == "__main__":
    print("🔧 Setting up database...")
    init_db()