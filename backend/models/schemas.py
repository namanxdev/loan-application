# -*- coding: utf-8 -*-
"""
Data Models and Schemas
- Pydantic models for API request/response validation
- SQLAlchemy ORM models for PostgreSQL persistence
"""

import re
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey, Enum as SQLEnum
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
    MANUAL_REVIEW = "MANUAL_REVIEW"


class AgentDecision(str, Enum):
    """Agent decision types"""
    APPROVE = "approve"
    REJECT = "reject"
    REVIEW = "review"


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
    user_id: Optional[int] = None
    assigned_employee_id: Optional[int] = None
    human_override: bool = False
    override_reason: Optional[str] = None
    current_agent: Optional[str] = None
    final_decision: Optional[str] = None
    decision_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentResultResponse(BaseModel):
    """Schema for agent evaluation result"""
    id: int
    application_id: int
    agent_name: str
    agent_type: str
    score: Optional[int]
    decision: str
    confidence: int
    explanation_summary: str
    detailed_analysis: Optional[dict] = None
    processing_time_ms: Optional[int] = None
    processed_at: datetime
    
    class Config:
        from_attributes = True


class StatusOverrideRequest(BaseModel):
    """Schema for employee status override"""
    new_status: str
    reason: str = Field(..., min_length=10, max_length=500)


# ============== SQLAlchemy ORM Models ==============

class Application(Base):
    """
    SQLAlchemy ORM model for loan applications.
    Maps to 'applications' table in PostgreSQL.
    """
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # User relationship (optional for backward compatibility)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Application Details
    customer_name = Column(String(100), nullable=False)
    mobile = Column(String(10), nullable=False)
    pan = Column(String(10), nullable=False)
    aadhaar = Column(String(12), nullable=False)
    loan_amount = Column(Integer, nullable=False)
    tenure = Column(Integer, nullable=False)
    income = Column(Integer, nullable=False)
    
    # KYC Details (stored as JSON for flexibility)
    kyc_details = Column(JSON, default=dict)
    
    # Processing
    status = Column(String(20), default="CREATED")
    workflow_steps = Column(JSON, default=list)
    current_agent = Column(String(50), nullable=True)
    
    # Results
    sanction_pdf_path = Column(String(255), nullable=True)
    final_decision = Column(String(20), nullable=True)
    decision_reason = Column(String(500), nullable=True)
    
    # Human Review
    assigned_employee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    human_override = Column(Boolean, default=False)
    override_reason = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="applications")
    assigned_employee = relationship("User", foreign_keys=[assigned_employee_id], back_populates="assigned_applications")
    agent_evaluations = relationship("AgentEvaluation", back_populates="application", cascade="all, delete-orphan")
    status_history = relationship("StatusHistory", back_populates="application", cascade="all, delete-orphan")
    conversation_sessions = relationship("ConversationSession", back_populates="application")

    def __repr__(self):
        return f"<Application(id={self.id}, customer={self.customer_name}, status={self.status})>"


class AgentEvaluation(Base):
    """
    SQLAlchemy ORM model for agent evaluation results.
    Stores individual agent decisions and scores.
    """
    __tablename__ = "agent_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    
    agent_name = Column(String(50), nullable=False)  # e.g., "AgentAlpha"
    agent_type = Column(String(50), nullable=False)  # e.g., "sales_validation"
    
    # Evaluation Results
    score = Column(Integer, nullable=True)  # 0-100
    decision = Column(String(20), nullable=False)  # approve/reject/review
    confidence = Column(Integer, default=100)  # 0-100%
    
    # Explanation
    explanation_summary = Column(String(500), nullable=False)
    detailed_analysis = Column(JSON, default=dict)
    
    # Processing
    processing_time_ms = Column(Integer, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    application = relationship("Application", back_populates="agent_evaluations")

    def __repr__(self):
        return f"<AgentEvaluation(app={self.application_id}, agent={self.agent_name}, decision={self.decision})>"


class StatusHistory(Base):
    """
    SQLAlchemy ORM model for application status changes.
    Tracks all status transitions for audit.
    """
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    
    old_status = Column(String(20), nullable=False)
    new_status = Column(String(20), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(String(500), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    application = relationship("Application", back_populates="status_history")
    changed_by = relationship("User")

    def __repr__(self):
        return f"<StatusHistory(app={self.application_id}, {self.old_status} -> {self.new_status})>"


class ConversationSession(Base):
    """
    SQLAlchemy ORM model for conversation sessions.
    Maps to 'conversation_sessions' table in PostgreSQL.
    """
    __tablename__ = "conversation_sessions"

    session_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    messages = Column(JSON, default=list)
    collected_data = Column(JSON, default=dict)
    stage = Column(String(50), default="greeting")
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    processing_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="conversation_sessions")
    user = relationship("User")

    def __repr__(self):
        return f"<ConversationSession(id={self.session_id}, stage={self.stage}, active={self.is_active})>"
