"""
Data Models and Schemas
- Pydantic models for API request/response validation
- SQLAlchemy ORM model for PostgreSQL persistence
"""

import re
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from services.database import Base


# ============== Enums ==============

class ApplicationStatus(str, Enum):
    """Status values for loan applications"""
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    SANCTIONED = "SANCTIONED"
    REJECTED = "REJECTED"


# ============== Pydantic Schemas (Request/Response) ==============

class ApplicationCreate(BaseModel):
    """Schema for creating a new loan application"""
    customer_name: str = Field(..., min_length=2, max_length=100)
    mobile: str = Field(..., pattern=r"^\d{10}$")
    pan: str = Field(..., min_length=10, max_length=10)
    aadhaar: str = Field(..., min_length=12, max_length=12)
    loan_amount: int = Field(..., gt=0)
    tenure: int = Field(..., gt=0, le=360)
    income: int = Field(..., gt=0)

    @field_validator("pan")
    @classmethod
    def validate_pan_format(cls, v: str) -> str:
        """Validate PAN format: ABCDE1234F"""
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", v.upper()):
            raise ValueError("Invalid PAN format. Expected: ABCDE1234F")
        return v.upper()

    @field_validator("aadhaar")
    @classmethod
    def validate_aadhaar_format(cls, v: str) -> str:
        """Validate Aadhaar is 12 digits"""
        if not v.isdigit() or len(v) != 12:
            raise ValueError("Aadhaar must be exactly 12 digits")
        return v


class ApplicationResponse(BaseModel):
    """Schema for application creation response"""
    application_id: int
    status: str


class StepResult(BaseModel):
    """Schema for individual workflow step result"""
    node: str
    result: str  # SUCCESS or FAIL
    data: Optional[dict] = None
    message: Optional[str] = None


class ProcessResponse(BaseModel):
    """Schema for workflow processing response"""
    status: str
    sanction_pdf_url: Optional[str] = None
    steps: List[StepResult]
    error_message: Optional[str] = None


class ApplicationDetail(BaseModel):
    """Schema for full application details"""
    id: int
    customer_name: str
    mobile: str
    pan: str
    aadhaar: str
    loan_amount: int
    tenure: int
    income: int
    status: str
    sanction_pdf_path: Optional[str] = None
    workflow_steps: Optional[List[Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============== SQLAlchemy ORM Model ==============

class Application(Base):
    """
    SQLAlchemy ORM model for loan applications.
    Maps to 'applications' table in PostgreSQL.
    """
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_name = Column(String(100), nullable=False)
    mobile = Column(String(10), nullable=False)
    pan = Column(String(10), nullable=False)
    aadhaar = Column(String(12), nullable=False)
    loan_amount = Column(Integer, nullable=False)
    tenure = Column(Integer, nullable=False)
    income = Column(Integer, nullable=False)
    status = Column(String(20), default="CREATED")
    sanction_pdf_path = Column(String(255), nullable=True)
    workflow_steps = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Application(id={self.id}, customer={self.customer_name}, status={self.status})>"


class ConversationSession(Base):
    """
    SQLAlchemy ORM model for conversation sessions.
    Maps to 'conversation_sessions' table in PostgreSQL.
    
    Stores chat session state for persistent conversation management.
    Will be migrated to Redis for production deployment.
    """
    __tablename__ = "conversation_sessions"

    session_id = Column(String(36), primary_key=True, index=True)
    messages = Column(JSON, default=list)
    collected_data = Column(JSON, default=dict)
    stage = Column(String(50), default="greeting")
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    processing_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to Application
    application = relationship("Application", backref="conversation_sessions")

    def __repr__(self):
        return f"<ConversationSession(id={self.session_id}, stage={self.stage}, active={self.is_active})>"
