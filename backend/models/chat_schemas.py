"""
Chat Schemas - Pydantic models for chat-based loan application

Defines request/response models for the conversational interface.
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    """Role of a message in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationStage(str, Enum):
    """Current stage in the loan application conversation"""
    GREETING = "greeting"
    COLLECTING_INFO = "collecting_info"
    SALES_DISCUSSION = "sales_discussion"
    KYC_VERIFICATION = "kyc_verification"
    UNDERWRITING = "underwriting"
    SANCTION = "sanction"
    COMPLETED = "completed"
    REJECTED = "rejected"


# ============== Request Schemas ==============

class ChatMessage(BaseModel):
    """A single message in the conversation"""
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class StartChatRequest(BaseModel):
    """Request to start a new chat session"""
    session_id: Optional[str] = None  # Optional, will be generated if not provided


class ChatRequest(BaseModel):
    """Request for sending a chat message"""
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, max_length=1000, description="User's message")


class ProcessApplicationRequest(BaseModel):
    """Request to process the complete application"""
    session_id: str = Field(..., description="Session ID with complete application data")


# ============== Response Schemas ==============

class StartChatResponse(BaseModel):
    """Response when starting a new chat"""
    session_id: str
    greeting: str
    stage: str
    timestamp: datetime
    active_agent: str = "master_agent"


class AgentThinking(BaseModel):
    """Agent's thinking/reasoning process"""
    agent_name: str
    action: str
    reasoning: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response to a chat message"""
    session_id: str
    response: str
    stage: str
    collected_data: Dict[str, Any]
    missing_fields: List[str]
    ready_to_process: bool
    timestamp: datetime
    active_agent: str = "master_agent"
    thinking: Optional[List[AgentThinking]] = None
    metadata: Optional[Dict[str, Any]] = None


class ProcessingStep(BaseModel):
    """A step in the application processing"""
    agent: str
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ApplicationProcessResponse(BaseModel):
    """Response after processing the application"""
    session_id: str
    status: str  # SANCTIONED, REJECTED, FAIL
    message: str
    steps: List[ProcessingStep]
    sanction_pdf_url: Optional[str] = None
    application_id: Optional[int] = None
    timestamp: datetime


class ConversationHistory(BaseModel):
    """Full conversation history for a session"""
    session_id: str
    messages: List[ChatMessage]
    current_stage: str
    collected_data: Dict[str, Any]
    application_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class SessionStatus(BaseModel):
    """Current status of a chat session"""
    session_id: str
    stage: str
    collected_data: Dict[str, Any]
    missing_fields: List[str]
    ready_to_process: bool
    application_id: Optional[int] = None
    is_active: bool


# ============== Agent Action Schemas ==============

class AgentAction(BaseModel):
    """An action taken by an agent"""
    agent_name: str
    action_type: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    success: bool
    message: str
    timestamp: datetime


class AgentHandoff(BaseModel):
    """Handoff between agents"""
    from_agent: str
    to_agent: str
    reason: str
    context: Dict[str, Any]
    timestamp: datetime
