"""DTOs for the Web Chat Interface."""
from pydantic import BaseModel, Field


class ChatRequestDTO(BaseModel):
    """Data Transfer Object for chat requests."""
    message: str = Field(..., min_length=1, max_length=4000, description="The user's chat message")
    session_id: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_\-]+$", description="The unique session identifier")


class ChatResponseDTO(BaseModel):
    """Data Transfer Object for chat responses."""
    response: str = Field(..., description="The agent's text response")
    status: str = Field(default="success", description="Status of the response")

