from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.node import Node
from app.core.security import hash_api_key

bearer_scheme = HTTPBearer()

def get_current_node(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Node:
    api_key_hash = hash_api_key(credentials.credentials)
    node = db.query(Node).filter(Node.api_key_hash == api_key_hash).first()
    if not node:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return node