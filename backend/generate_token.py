import secrets
from app.db import SessionLocal
from app.models.enrollment_token import EnrollmentToken

def create_token():
    token_value = secrets.token_hex(32)
    db = SessionLocal()
    token = EnrollmentToken(token=token_value)
    db.add(token)
    db.commit()
    db.close()
    print(f"\nEnrollment token:\n\n  {token_value}\n")

if __name__ == "__main__":
    create_token()