"""
Run this once (or after schema changes) to create all tables:

    python init_db.py

It is safe to run repeatedly — SQLAlchemy's create_all() is a no-op
for tables that already exist.  For production schema migrations use
Alembic instead.
"""

from app.db import Base, engine

# Import every model so SQLAlchemy's metadata is populated before
# create_all() is called.  The import itself is the side-effect we need.
import app.models  # noqa: F401 — triggers __init__.py which imports all models

if __name__ == "__main__":
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Done.")
