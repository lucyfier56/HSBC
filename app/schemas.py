from pydantic import BaseModel
from typing import Optional, Dict, Any

class UserRequest(BaseModel):
    user_id: str
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    state: Optional[Dict[str, Any]] = None
    requires_selection: Optional[bool] = False
    options: Optional[list] = None

class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class LLMResponse(BaseModel):
    text: str
    has_tool_call: bool = False
    tool_call: Optional[ToolCall] = None
