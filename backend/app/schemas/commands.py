from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class CommandOut(BaseModel):
    command_id: str
    type: str
    payload: Dict[str, Any]

class PendingCommandsResponse(BaseModel):
    commands: List[CommandOut]

class CommandResultRequest(BaseModel):
    node_id: int
    command_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None