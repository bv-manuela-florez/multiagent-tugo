from typing import List, Literal
from utils.cosmos_utils_orm import CosmosModel  # <-- Importa CosmosModel
from pydantic import BaseModel


class User(BaseModel):
    user_id: str
    user_name: str | None = None
    user_email: str | None = None


class ConversationChatInput(BaseModel):
    type: str = "Request"
    channel: str | None = None
    session_id: str
    user_id: User
    message: str
    attachments: List[str] | None = None


class Citation (BaseModel):
    position: int
    citationTitle: str
    citationUrl: str
    abstract: str | None = None


class TokenUsage(BaseModel):
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int


class ConversationChatResponse(BaseModel):
    type: str = "Response"
    thread_id: str
    task_id: str | None = None
    task_status: str | None = None
    context_id: str | None = None
    agent: str
    agent_id: str | None = None
    agent_prompt: str | None = None
    agent_tools: List[str] | None = None
    content: str
    images: List[str] | None = None
    citations: List[Citation] | None = None


class ConversationChat(CosmosModel):  # <-- Cambia BaseModel por CosmosModel
    conversation_status: Literal["InProgress", "Completed"]
    session_id: str
    user_id: str
    datetime: str
    updated_at: str | None = None
    token_usage: TokenUsage | None = None
    feedback: bool | None = None
    input: ConversationChatInput | None = None
    response: ConversationChatResponse | None = None

    class Meta:
        container_name = "ConversationChat"
        partition_key = "session_id"
