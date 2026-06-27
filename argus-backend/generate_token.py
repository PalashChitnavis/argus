import secrets
from app.db import SessionLocal
from app.models.enrollment_token import EnrollmentToken
import app.models  # noqa: registers all models

def create_token():
    db = SessionLocal()
    token_value = secrets.token_urlsafe(32)
    token = EnrollmentToken(token=token_value)
    db.add(token)
    db.commit()
    print(f"Created enrollment token: {token_value}")
    db.close()

if __name__ == "__main__":
    create_token()