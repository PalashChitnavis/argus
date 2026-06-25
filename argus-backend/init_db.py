from app.db import Base, engine
import app.models  # noqa: F401 — imported for its side effect of registering models with Base

Base.metadata.create_all(bind=engine)
print("Tables created successfully.")