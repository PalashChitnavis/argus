from pydantic import BaseModel

class RegisterRequest(BaseModel):
    enrollment_token: str
    machine_id: str
    hostname: str

class RegisterResponse(BaseModel):
    node_id: int
    api_key: str