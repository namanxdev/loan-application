# -*- coding: utf-8 -*-
"""
User Models and Schemas
- Pydantic models for auth request/response validation
- SQLAlchemy ORM model for user persistence
"""

import re
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, EmailStr, field_validator
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from services.database import Base


# ============== Enums ==============

class UserRole(str, Enum):
    """User role types"""
    CUSTOMER = "customer"
    EMPLOYEE = "employee"
    ADMIN = "admin"


class KYCStatus(str, Enum):
    """KYC verification status"""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


# ============== SQLAlchemy ORM Model ==============

class User(Base):
    """
    SQLAlchemy ORM model for users.
    Maps to 'users' table in PostgreSQL.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(15), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Personal Info
    full_name = Column(String(100), nullable=False)
    aadhaar = Column(String(12), nullable=True)
    pan = Column(String(10), nullable=True)
    monthly_income = Column(Integer, nullable=True)
    
    # KYC & Verification
    kyc_status = Column(SQLEnum(KYCStatus), default=KYCStatus.NOT_STARTED)
    kyc_verified_at = Column(DateTime, nullable=True)
    verification_result = Column(String(500), nullable=True)
    
    # Role & Status
    role = Column(SQLEnum(UserRole), default=UserRole.CUSTOMER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    applications = relationship("Application", back_populates="user", foreign_keys="Application.user_id")
    assigned_applications = relationship("Application", back_populates="assigned_employee", foreign_keys="Application.assigned_employee_id")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


# ============== Pydantic Schemas (Request/Response) ==============

class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    phone: str = Field(..., pattern=r"^\d{10}$")
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\d{10}$")
    aadhaar: Optional[str] = None
    pan: Optional[str] = None
    monthly_income: Optional[int] = None
    
    @field_validator("pan")
    @classmethod
    def validate_pan_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", v.upper()):
                raise ValueError("Invalid PAN format. Expected: ABCDE1234F")
            return v.upper()
        return v
    
    @field_validator("aadhaar")
    @classmethod
    def validate_aadhaar_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = re.sub(r'[\s-]', '', v)
            if not clean.isdigit() or len(clean) != 12:
                raise ValueError("Aadhaar must be exactly 12 digits")
            return clean
        return v


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    email: str
    phone: str
    full_name: str
    role: UserRole
    kyc_status: KYCStatus
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str

