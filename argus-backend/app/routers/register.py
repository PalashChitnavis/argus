from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.enrollment_token import EnrollmentToken
from app.models.node import Node
from app.schemas.register import RegisterRequest, RegisterResponse
from app.core.security import generate_api_key, hash_api_key

router = APIRouter()

@router.post("/register", response_model=RegisterResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # 1. Look up the token
    token = db.query(EnrollmentToken).filter(
        EnrollmentToken.token == request.enrollment_token
    ).first()

    if not token:
        raise HTTPException(status_code=401, detail="Invalid enrollment token")

    if token.used:
        raise HTTPException(status_code=401, detail="Enrollment token already used")

    # 2. Check for duplicate machine_id
    existing = db.query(Node).filter(
        Node.machine_id == request.machine_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Machine already registered")

    # 3. Generate the api_key
    raw_key = generate_api_key()
    hashed_key = hash_api_key(raw_key)

    # 4. Create the node row
    node = Node(
        machine_id=request.machine_id,
        hostname=request.hostname,
        api_key_hash=hashed_key,
    )
    db.add(node)
    db.flush()  # assigns node.id without committing yet

    # 5. Mark the token as used
    token.used = True
    token.used_by_node_id = node.id

    # 6. Commit everything atomically
    db.commit()
    db.refresh(node)

    return RegisterResponse(node_id=node.id, api_key=raw_key)