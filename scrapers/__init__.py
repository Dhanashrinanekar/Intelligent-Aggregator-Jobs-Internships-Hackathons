# database/__init__.py

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from db_operations module
from database.db_operations import JobDatabase

__all__ = ['JobDatabase']