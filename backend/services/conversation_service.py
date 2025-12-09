"""
Conversation Service - Manages chat sessions and conversation state

Handles:
- Session creation and management
- Conversation history storage
- State persistence
- Memory management for RAG context
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from collections import defaultdict
import threading


class ConversationSession:
    """Represents a single conversation session"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Dict[str, Any]] = []
        self.collected_data: Dict[str, Any] = {}
        self.stage: str = "greeting"
        self.application_id: Optional[int] = None
        self.is_active: bool = True
        self.created_at: datetime = datetime.utcnow()
        self.updated_at: datetime = datetime.utcnow()
        self.processing_result: Optional[Dict[str, Any]] = None
        
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the conversation history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
        self.updated_at = datetime.utcnow()
    
    def update_data(self, new_data: Dict[str, Any]):
        """Update collected application data"""
        self.collected_data.update(new_data)
        self.updated_at = datetime.utcnow()
    
    def set_stage(self, stage: str):
        """Update conversation stage"""
        self.stage = stage
        self.updated_at = datetime.utcnow()
    
    def set_application_id(self, app_id: int):
        """Set the database application ID"""
        self.application_id = app_id
        self.updated_at = datetime.utcnow()
    
    def set_processing_result(self, result: Dict[str, Any]):
        """Store processing result"""
        self.processing_result = result
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Mark session as inactive"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "processing_result": self.processing_result
        }


class ConversationManager:
    """
    Manages all conversation sessions.
    
    This is an in-memory implementation. For production, 
    consider using Redis or a database for persistence.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for conversation manager"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.sessions: Dict[str, ConversationSession] = {}
        self._lock = threading.Lock()
        self._initialized = True
    
    def create_session(self, session_id: Optional[str] = None) -> ConversationSession:
        """Create a new conversation session"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        with self._lock:
            if session_id in self.sessions:
                # Return existing session
                return self.sessions[session_id]
            
            session = ConversationSession(session_id)
            self.sessions[session_id] = session
            return session
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get an existing session by ID"""
        return self.sessions.get(session_id)
    
    def get_or_create_session(self, session_id: str) -> ConversationSession:
        """Get existing session or create new one"""
        session = self.get_session(session_id)
        if session is None:
            session = self.create_session(session_id)
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
    
    def list_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return [
            sid for sid, session in self.sessions.items() 
            if session.is_active
        ]
    
    def get_session_count(self) -> int:
        """Get total number of sessions"""
        return len(self.sessions)
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than specified hours"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        with self._lock:
            to_delete = [
                sid for sid, session in self.sessions.items()
                if session.updated_at < cutoff
            ]
            for sid in to_delete:
                del self.sessions[sid]
        
        return len(to_delete)


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
        - Loan amounts from ₹10,000 to ₹50,00,000
        - Tenure from 6 months to 30 years (360 months)
        - Competitive interest rates starting at 10.5% p.a.
        - No hidden charges
        - Quick approval within 24 hours
        """,
        
        "eligibility": """
        Loan Eligibility Criteria:
        - Age: 21-60 years
        - Minimum income: ₹15,000 per month
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
