# -*- coding: utf-8 -*-
"""
Conversation Service - Manages chat sessions and conversation state

Handles:
- Session creation and management
- Conversation history storage
- State persistence using PostgreSQL
- Memory management for RAG context

Note: This implementation uses PostgreSQL for persistence.
For production at scale, migrate to Redis for better performance.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from sqlalchemy.orm import Session as DBSession
from services.database import SessionLocal
from models.schemas import ConversationSession as ConversationSessionModel


class ConversationSession:
    """
    Represents a single conversation session.
    Wrapper class that interfaces with the database model.
    """
    
    def __init__(self, session_id: str, db_session: Optional[ConversationSessionModel] = None):
        self.session_id = session_id
        self._db_model = db_session
        
        # Load from database model or initialize defaults
        if db_session:
            self.messages: List[Dict[str, Any]] = db_session.messages or []
            self.collected_data: Dict[str, Any] = db_session.collected_data or {}
            self.stage: str = db_session.stage or "greeting"
            self.application_id: Optional[int] = db_session.application_id
            self.is_active: bool = db_session.is_active
            self.created_at: datetime = db_session.created_at
            self.updated_at: datetime = db_session.updated_at
            self.processing_result: Optional[Dict[str, Any]] = db_session.processing_result
        else:
            self.messages = []
            self.collected_data = {}
            self.stage = "greeting"
            self.application_id = None
            self.is_active = True
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
            self.processing_result = None
    
    def _save_to_db(self):
        """Save current state to database"""
        db = SessionLocal()
        try:
            db_session = db.query(ConversationSessionModel).filter(
                ConversationSessionModel.session_id == self.session_id
            ).first()
            
            if db_session:
                db_session.messages = self.messages
                db_session.collected_data = self.collected_data
                db_session.stage = self.stage
                db_session.application_id = self.application_id
                db_session.is_active = self.is_active
                db_session.processing_result = self.processing_result
                db_session.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
        
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the conversation history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
        self.updated_at = datetime.utcnow()
        self._save_to_db()
    
    def update_data(self, new_data: Dict[str, Any]):
        """Update collected application data"""
        self.collected_data.update(new_data)
        self.updated_at = datetime.utcnow()
        self._save_to_db()
    
    def set_stage(self, stage: str):
        """Update conversation stage"""
        self.stage = stage
        self.updated_at = datetime.utcnow()
        self._save_to_db()
    
    def set_application_id(self, app_id: int):
        """Set the database application ID"""
        self.application_id = app_id
        self.updated_at = datetime.utcnow()
        self._save_to_db()
    
    def set_processing_result(self, result: Dict[str, Any]):
        """Store processing result"""
        self.processing_result = result
        self.updated_at = datetime.utcnow()
        self._save_to_db()
    
    def deactivate(self):
        """Mark session as inactive"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
        self._save_to_db()
    
    def get_context_window(self, max_messages: int = 10) -> List[Dict]:
        """Get recent messages for context"""
        return self.messages[-max_messages:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "collected_data": self.collected_data,
            "stage": self.stage,
            "application_id": self.application_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "processing_result": self.processing_result
        }


class ConversationManager:
    """
    Manages all conversation sessions using PostgreSQL for persistence.
    
    Uses SQLAlchemy ORM to store sessions in the conversation_sessions table.
    Maintains the same public API as the in-memory implementation for 
    compatibility with existing code.
    
    For production at scale, migrate to Redis for better performance.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for conversation manager"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
    
    @contextmanager
    def _get_db(self):
        """Context manager for database sessions"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def create_session(self, session_id: Optional[str] = None) -> ConversationSession:
        """Create a new conversation session in the database"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        with self._get_db() as db:
            # Check if session already exists
            existing = db.query(ConversationSessionModel).filter(
                ConversationSessionModel.session_id == session_id
            ).first()
            
            if existing:
                return ConversationSession(session_id, existing)
            
            # Create new session in database
            db_session = ConversationSessionModel(
                session_id=session_id,
                messages=[],
                collected_data={},
                stage="greeting",
                is_active=True
            )
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            
            return ConversationSession(session_id, db_session)
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get an existing session by ID from the database"""
        with self._get_db() as db:
            db_session = db.query(ConversationSessionModel).filter(
                ConversationSessionModel.session_id == session_id
            ).first()
            
            if db_session:
                return ConversationSession(session_id, db_session)
            return None
    
    def get_or_create_session(self, session_id: str) -> ConversationSession:
        """Get existing session or create new one"""
        session = self.get_session(session_id)
        if session is None:
            session = self.create_session(session_id)
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session from the database"""
        with self._get_db() as db:
            db_session = db.query(ConversationSessionModel).filter(
                ConversationSessionModel.session_id == session_id
            ).first()
            
            if db_session:
                db.delete(db_session)
                db.commit()
                return True
            return False
    
    def list_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        with self._get_db() as db:
            sessions = db.query(ConversationSessionModel.session_id).filter(
                ConversationSessionModel.is_active == True
            ).all()
            return [s.session_id for s in sessions]
    
    def get_session_count(self) -> int:
        """Get total number of sessions"""
        with self._get_db() as db:
            return db.query(ConversationSessionModel).count()
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Remove sessions older than specified hours"""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        with self._get_db() as db:
            deleted = db.query(ConversationSessionModel).filter(
                ConversationSessionModel.updated_at < cutoff
            ).delete()
            db.commit()
            return deleted


class RAGContextBuilder:
    """
    Builds context for RAG-based responses.
    
    Combines conversation history with relevant knowledge
    to create rich context for the AI model.
    """
    
    # Knowledge base for loan-related information
    KNOWLEDGE_BASE = {
        "loan_types": """
        We offer personal loans with the following features:
        - Loan amounts from Rs.10,000 to Rs.50,00,000
        - Tenure from 6 months to 30 years (360 months)
        - Competitive interest rates starting at 10.5% p.a.
        - No hidden charges
        - Quick approval within 24 hours
        """,
        
        "eligibility": """
        Loan Eligibility Criteria:
        - Age: 21-60 years
        - Minimum income: Rs.15,000 per month
        - Credit score: 600+ preferred
        - EMI should not exceed 50% of monthly income
        - Maximum loan: 50x monthly income
        """,
        
        "documents": """
        Required Documents:
        - PAN Card (for identity and tax verification)
        - Aadhaar Card (for identity and address proof)
        - Mobile number (for OTP verification)
        - Income proof may be requested for large loans
        """,
        
        "process": """
        Loan Application Process:
        1. Submit basic details (name, contact, documents)
        2. Choose loan amount and tenure
        3. Automated KYC verification
        4. Credit assessment and eligibility check
        5. Instant approval/rejection decision
        6. Sanction letter generation for approved loans
        7. Disbursement within 24-48 hours
        """,
        
        "emi_info": """
        EMI Calculation:
        - We use reducing balance method
        - Standard interest rate: 12% per annum
        - EMI = [P x R x (1+R)^N] / [(1+R)^N - 1]
        - P = Principal, R = Monthly rate, N = Tenure in months
        """,
        
        "security": """
        Data Security:
        - All data is encrypted in transit and at rest
        - We comply with RBI guidelines
        - Your information is never shared without consent
        - Secure document verification process
        """
    }
    
    @classmethod
    def build_context(
        cls,
        session: ConversationSession,
        user_query: str,
        include_knowledge: List[str] = None
    ) -> str:
        """
        Build comprehensive context for AI response.
        
        Args:
            session: Current conversation session
            user_query: User's latest message
            include_knowledge: List of knowledge topics to include
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add conversation history
        context_parts.append("## Conversation History:")
        for msg in session.get_context_window():
            role = "Customer" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        
        # Add collected data
        if session.collected_data:
            context_parts.append("\n## Collected Application Data:")
            for key, value in session.collected_data.items():
                context_parts.append(f"- {key}: {value}")
        
        # Add relevant knowledge
        if include_knowledge:
            context_parts.append("\n## Reference Information:")
            for topic in include_knowledge:
                if topic in cls.KNOWLEDGE_BASE:
                    context_parts.append(cls.KNOWLEDGE_BASE[topic])
        
        # Auto-detect relevant knowledge based on query
        else:
            relevant_topics = cls._detect_relevant_topics(user_query)
            if relevant_topics:
                context_parts.append("\n## Reference Information:")
                for topic in relevant_topics:
                    context_parts.append(cls.KNOWLEDGE_BASE[topic])
        
        # Add current stage info
        context_parts.append(f"\n## Current Stage: {session.stage}")
        
        # Add user query
        context_parts.append(f"\n## Customer Query: {user_query}")
        
        return "\n".join(context_parts)
    
    @classmethod
    def _detect_relevant_topics(cls, query: str) -> List[str]:
        """Detect which knowledge topics are relevant to the query"""
        query_lower = query.lower()
        relevant = []
        
        # Simple keyword matching - could be enhanced with embeddings
        keyword_map = {
            "loan_types": ["interest", "rate", "types", "features", "loan amount"],
            "eligibility": ["eligible", "qualify", "criteria", "requirement", "credit score"],
            "documents": ["document", "pan", "aadhaar", "proof", "kyc"],
            "process": ["process", "steps", "how", "procedure", "apply"],
            "emi_info": ["emi", "installment", "monthly", "payment", "calculate"],
            "security": ["secure", "privacy", "data", "safe", "protection"]
        }
        
        for topic, keywords in keyword_map.items():
            if any(kw in query_lower for kw in keywords):
                relevant.append(topic)
        
        return relevant[:2]  # Limit to 2 most relevant


# Create singleton instance
conversation_manager = ConversationManager()
