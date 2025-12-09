"""
Master Agent - LangChain/LangGraph Based Orchestrator

Uses LangChain's ChatGoogleGenerativeAI and LangGraph for:
1. Conversational loan application flow
2. Multi-agent orchestration
3. State management and routing

Workflow:
1. Customer lands on chatbot → Master Agent
2. Discusses loan amount & terms → Sales Agent  
3. Performs KYC verification → Verification Agent
4. Checks credit score, salary, eligibility → Underwriting Agent
5. Generates sanction letter → Sanction Agent
6. Customer receives instant approval/rejection → Master Agent
"""

import os
import json
from typing import Any, Optional, List
from enum import Enum

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


# ============== Pydantic Models for Structured Output ==============

class ExtractedInfo(BaseModel):
    """Extracted application information from user message"""
    customer_name: Optional[str] = Field(None, description="Customer's full name")
    mobile: Optional[str] = Field(None, description="10-digit mobile number")
    pan: Optional[str] = Field(None, description="PAN number in format ABCDE1234F")
    aadhaar: Optional[str] = Field(None, description="12-digit Aadhaar number")
    loan_amount: Optional[int] = Field(None, description="Loan amount in rupees")
    tenure: Optional[int] = Field(None, description="Loan tenure in months")
    income: Optional[int] = Field(None, description="Monthly income in rupees")


class ConversationStage(str, Enum):
    """Stages in the loan application conversation"""
    GREETING = "greeting"
    COLLECTING_INFO = "collecting_info"
    CONFIRMING = "confirming"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


# Required fields
REQUIRED_FIELDS = ["customer_name", "mobile", "pan", "aadhaar", "loan_amount", "tenure", "income"]


# ============== LangChain Components ==============

def get_llm(temperature: float = 0.7) -> ChatGoogleGenerativeAI:
    """Get configured Gemini LLM via LangChain"""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=temperature,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )


# ============== Master Agent ==============

class MasterAgent:
    """
    Master Agent using LangChain for orchestrating loan conversations.
    """
    
    def __init__(self):
        self.llm = get_llm(temperature=0.7)
        self.extraction_llm = get_llm(temperature=0)
        self._setup_chains()
    
    def _setup_chains(self):
        """Setup LangChain chains for different tasks"""
        
        # Chain for extracting information from user messages
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an information extraction assistant. Extract loan application details from the user message.

Current collected data: {current_data}

Extract ONLY new information not already in current data. Return a JSON object with these fields (only include fields with clear values):
- customer_name: Full name (string)
- mobile: 10-digit mobile number (string, digits only)
- pan: PAN number format ABCDE1234F (string, uppercase)
- aadhaar: 12-digit Aadhaar number (string, digits only)  
- loan_amount: Loan amount in rupees (integer, convert lakhs: 1 lakh = 100000)
- tenure: Loan tenure in months (integer)
- income: Monthly income in rupees (integer)

Return empty object {{}} if no new information found. Return ONLY valid JSON."""),
            ("human", "{message}")
        ])
        self.extraction_chain = extraction_prompt | self.extraction_llm | JsonOutputParser()
        
        # Chain for generating conversational responses
        conversation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a friendly Loan Application Assistant. Guide customers through the loan process conversationally.

## Your Responsibilities:
- Welcome customers and explain the loan process
- Collect required information naturally (1-2 items at a time)
- Validate and confirm information
- Keep customers informed about progress

## Required Information:
- Customer Name, Mobile (10 digits), PAN (ABCDE1234F format)
- Aadhaar (12 digits), Loan Amount (min ₹10,000)
- Tenure (6-360 months), Monthly Income

## Current State:
Stage: {stage}
Collected Data: {collected_data}
Missing Fields: {missing_fields}

## Guidelines:
- Be conversational, not robotic
- Use ₹ for currency
- Ask for 1-2 pieces of info at a time
- If all info collected, confirm details and ask to proceed"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{message}")
        ])
        self.conversation_chain = conversation_prompt | self.llm | StrOutputParser()
        
        # Chain for generating greetings
        greeting_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a friendly Loan Application Assistant. Generate a warm welcome message.
- Introduce yourself briefly
- Explain you'll guide them through a quick loan application
- Ask for their name to get started
- Keep it concise (2-3 sentences)"""),
            ("human", "Generate a greeting for a new customer starting a loan application.")
        ])
        self.greeting_chain = greeting_prompt | self.llm | StrOutputParser()
    
    def extract_info(self, message: str, current_data: dict) -> dict:
        """Extract application info from user message using LangChain"""
        try:
            result = self.extraction_chain.invoke({
                "message": message,
                "current_data": json.dumps(current_data)
            })
            return result if isinstance(result, dict) else {}
        except Exception as e:
            print(f"Extraction error: {e}")
            return {}
    
    def get_missing_fields(self, data: dict) -> List[str]:
        """Get list of missing required fields"""
        return [f for f in REQUIRED_FIELDS if not data.get(f)]
    
    def generate_response(
        self,
        message: str,
        history: List[BaseMessage],
        current_data: dict,
        stage: str
    ) -> str:
        """Generate conversational response using LangChain"""
        missing = self.get_missing_fields(current_data)
        
        # Field name mapping for display
        field_names = {
            "customer_name": "name",
            "mobile": "mobile number", 
            "pan": "PAN number",
            "aadhaar": "Aadhaar number",
            "loan_amount": "loan amount",
            "tenure": "loan tenure",
            "income": "monthly income"
        }
        missing_display = [field_names.get(f, f) for f in missing]
        
        try:
            response = self.conversation_chain.invoke({
                "message": message,
                "history": history[-10:],  # Last 10 messages for context
                "stage": stage,
                "collected_data": json.dumps(current_data, indent=2) if current_data else "None yet",
                "missing_fields": ", ".join(missing_display) if missing_display else "All collected!"
            })
            return response
        except Exception as e:
            print(f"Response generation error: {e}")
            return "I apologize, but I'm having trouble. Could you please try again?"
    
    def get_greeting(self) -> str:
        """Generate initial greeting"""
        try:
            return self.greeting_chain.invoke({})
        except Exception as e:
            print(f"Greeting error: {e}")
            return "Welcome! I'm your loan application assistant. I'll help you apply for a loan quickly. May I have your name to get started?"
    
    def summarize_application(self, data: dict) -> str:
        """Generate application summary for confirmation"""
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """Create a friendly summary of this loan application for customer confirmation.
Format nicely with sections. Mask Aadhaar (show last 4 digits only).
End by asking if details are correct and if they want to proceed."""),
            ("human", "Application data: {data}")
        ])
        chain = summary_prompt | self.llm | StrOutputParser()
        
        try:
            return chain.invoke({"data": json.dumps(data, indent=2)})
        except:
            aadhaar = data.get('aadhaar', '')
            masked_aadhaar = f"XXXX-XXXX-{aadhaar[-4:]}" if len(aadhaar) >= 4 else aadhaar
            return f"""📋 **Application Summary**

**Personal Details:**
- Name: {data.get('customer_name', 'N/A')}
- Mobile: {data.get('mobile', 'N/A')}
- PAN: {data.get('pan', 'N/A')}
- Aadhaar: {masked_aadhaar}

**Loan Details:**
- Amount: ₹{data.get('loan_amount', 0):,}
- Tenure: {data.get('tenure', 0)} months
- Monthly Income: ₹{data.get('income', 0):,}

Does this look correct? Would you like to proceed?"""


# ============== Specialized Agent Responders ==============

class SalesAgentResponder:
    """Sales Agent for discussing loan terms"""
    
    def __init__(self):
        self.llm = get_llm(temperature=0.7)
    
    def discuss_terms(self, loan_amount: int, tenure: int, income: int) -> str:
        """Discuss loan terms with customer"""
        # Calculate EMI
        rate = 12 / 12 / 100
        emi = (loan_amount * rate * (1 + rate)**tenure) / ((1 + rate)**tenure - 1)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You're a loan sales assistant. Discuss these loan terms briefly:
- Loan: ₹{loan_amount:,}, Tenure: {tenure} months, EMI: ~₹{emi:,.0f}
- Income: ₹{income:,}/month, EMI ratio: {ratio:.1f}%
Be helpful and concise (2-3 sentences). Mention if EMI is affordable (<50% of income)."""),
            ("human", "Explain my loan terms.")
        ])
        
        try:
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke({
                "loan_amount": loan_amount,
                "tenure": tenure,
                "emi": emi,
                "income": income,
                "ratio": (emi / income) * 100
            })
        except:
            return f"Your loan of ₹{loan_amount:,} over {tenure} months has an EMI of ~₹{emi:,.0f}."


class VerificationAgentResponder:
    """Verification Agent for KYC process"""
    
    def __init__(self):
        self.llm = get_llm(temperature=0.5)
    
    def explain_kyc(self) -> str:
        """Explain KYC verification"""
        return "🔍 I'm now verifying your identity documents (PAN & Aadhaar). This is a quick automated check..."
    
    def report_result(self, verified: bool, details: dict) -> str:
        """Report verification results"""
        if verified:
            return "✅ Great news! Your identity verification is complete. All documents verified successfully."
        else:
            return f"❌ Verification issue: {details.get('error', 'Please check your document details.')}"


class UnderwritingAgentResponder:
    """Underwriting Agent for credit assessment"""
    
    def __init__(self):
        self.llm = get_llm(temperature=0.5)
    
    def explain_underwriting(self) -> str:
        """Explain underwriting process"""
        return "📊 Checking your credit profile and loan eligibility..."
    
    def report_result(self, approved: bool, details: dict) -> str:
        """Report underwriting results"""
        if approved:
            score = details.get('credit_score', 750)
            return f"✅ Excellent! Your credit score of {score} meets our requirements. You're eligible for this loan!"
        else:
            return f"❌ Unfortunately, the loan cannot be approved: {details.get('reason', 'Eligibility criteria not met.')}"


class SanctionAgentResponder:
    """Sanction Agent for loan approval"""
    
    def __init__(self):
        self.llm = get_llm(temperature=0.7)
    
    def announce_sanction(self, loan_amount: int, tenure: int, pdf_url: str) -> str:
        """Announce loan approval"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Announce loan approval enthusiastically!
Loan: ₹{loan_amount:,}, Tenure: {tenure} months
Sanction letter ready at: {pdf_url}
Be celebratory but professional. Mention next steps (download letter, disbursement in 24-48hrs)."""),
            ("human", "Announce my loan approval!")
        ])
        
        try:
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke({
                "loan_amount": loan_amount,
                "tenure": tenure,
                "pdf_url": pdf_url
            })
        except:
            return f"""🎉 **Congratulations!** Your loan of ₹{loan_amount:,} has been APPROVED!

📄 Your sanction letter is ready: {pdf_url}
💰 Disbursement within 24-48 hours.

Thank you for choosing us!"""


# ============== Singleton Instances ==============

master_agent = MasterAgent()
sales_responder = SalesAgentResponder()
verification_responder = VerificationAgentResponder()
underwriting_responder = UnderwritingAgentResponder()
sanction_responder = SanctionAgentResponder()
