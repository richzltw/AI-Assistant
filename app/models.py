from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1)
    session_id: Optional[str] = Field(default=None, max_length=128)
    enable_tools: bool = True


class ChatResponse(BaseModel):
    answer: str
    used_tool: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None


class VoiceSynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class ToolCall(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
