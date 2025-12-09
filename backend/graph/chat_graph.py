"""
Chat Graph - LangGraph Workflow for Conversational Loan Application

Uses LangGraph's StateGraph for multi-agent orchestration:
Master Agent → Sales Agent → Verification Agent → Underwriting Agent → Sanction Agent

Each agent node processes the application and generates conversational responses.
"""

from typing import TypedDict, Literal, Any, Optional, List, Annotated
from operator import add
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.master_agent import (
    master_agent,
    sales_responder,
    verification_responder,
    underwriting_responder,
    sanction_responder
)
from agents.sales_node import sales_node
from agents.verification_node import verification_node
from agents.underwriting_node import underwriting_node
from agents.sanction_node import sanction_node


# ============== State Schema with Message Accumulation ==============

class ChatState(TypedDict, total=False):
    """
    LangGraph state schema for conversational loan workflow.
    Uses Annotated types for message accumulation.
    """
    # Application data (from user)
    application_id: int
    customer_name: str
    mobile: str
    pan: str
    aadhaar: str
    loan_amount: int
    tenure: int
    income: int
    
    # LangGraph message history (accumulated)
    messages: Annotated[List[BaseMessage], add]
    
    # Agent responses (accumulated)  
    agent_responses: Annotated[List[str], add]
    
    # Workflow state
    status: str
    credit_score: int
    steps: Annotated[List[dict], add]
    current_agent: str
    sanction_pdf_url: Optional[str]
    error_message: Optional[str]
    
    # Final output
    final_response: str
    processing_complete: bool


# ============== Agent Node Functions ==============

def sales_agent_node(state: ChatState) -> dict:
    """
    Sales Agent Node - Validates application and discusses terms.
    
    Step 2: Discusses loan amount & terms
    """
    # Run validation logic
    result = sales_node(state)
    
    # Generate conversational response
    responses = []
    
    if result.get("status") == "SUCCESS":
        # Discuss loan terms
        terms_msg = sales_responder.discuss_terms(
            loan_amount=state.get("loan_amount", 0),
            tenure=state.get("tenure", 12),
            income=state.get("income", 0)
        )
        responses.append(f"💼 **Sales Agent**: {terms_msg}")
    else:
        error = result.get("error_message", "Validation failed")
        responses.append(f"💼 **Sales Agent**: I found some issues: {error}")
    
    return {
        **result,
        "agent_responses": responses,
        "current_agent": "sales",
        "messages": [AIMessage(content=responses[0])]
    }


def verification_agent_node(state: ChatState) -> dict:
    """
    Verification Agent Node - Performs KYC verification.
    
    Step 3: Performs KYC verification
    """
    responses = []
    
    # Pre-verification message
    responses.append(f"🔍 **Verification Agent**: {verification_responder.explain_kyc()}")
    
    # Run verification
    result = verification_node(state)
    
    # Get verification details
    steps = result.get("steps", [])
    verification_step = next((s for s in steps if s.get("node") == "verification"), {})
    details = verification_step.get("data", {})
    
    # Post-verification message
    verified = result.get("status") == "SUCCESS"
    result_msg = verification_responder.report_result(verified, details)
    responses.append(f"🔍 **Verification Agent**: {result_msg}")
    
    return {
        **result,
        "agent_responses": responses,
        "current_agent": "verification",
        "messages": [AIMessage(content=r) for r in responses]
    }


def underwriting_agent_node(state: ChatState) -> dict:
    """
    Underwriting Agent Node - Credit assessment and eligibility.
    
    Step 4: Checks credit score, salary, and eligibility
    """
    responses = []
    
    # Pre-underwriting message
    responses.append(f"📊 **Underwriting Agent**: {underwriting_responder.explain_underwriting()}")
    
    # Run underwriting
    result = underwriting_node(state)
    
    # Get underwriting details
    steps = result.get("steps", [])
    uw_step = next((s for s in steps if s.get("node") == "underwriting"), {})
    details = uw_step.get("data", {})
    
    # Post-underwriting message
    approved = result.get("status") == "SUCCESS"
    result_msg = underwriting_responder.report_result(approved, details)
    responses.append(f"📊 **Underwriting Agent**: {result_msg}")
    
    return {
        **result,
        "agent_responses": responses,
        "current_agent": "underwriting",
        "credit_score": details.get("credit_score", 750),
        "messages": [AIMessage(content=r) for r in responses]
    }


def sanction_agent_node(state: ChatState) -> dict:
    """
    Sanction Agent Node - Generates sanction letter.
    
    Step 5: Generates sanction letter
    """
    responses = []
    
    # Run sanction
    result = sanction_node(state)
    
    if result.get("status") == "SANCTIONED":
        pdf_url = result.get("sanction_pdf_url", "")
        sanction_msg = sanction_responder.announce_sanction(
            loan_amount=state.get("loan_amount", 0),
            tenure=state.get("tenure", 12),
            pdf_url=pdf_url
        )
        responses.append(f"📄 **Sanction Agent**: {sanction_msg}")
    else:
        responses.append("📄 **Sanction Agent**: There was an issue generating your sanction letter. Please contact support.")
    
    return {
        **result,
        "agent_responses": responses,
        "current_agent": "sanction",
        "messages": [AIMessage(content=responses[0])]
    }


def master_result_node(state: ChatState) -> dict:
    """
    Master Agent Result Node - Compiles final response.
    
    Step 6: Customer receives instant approval/rejection
    """
    status = state.get("status", "FAIL")
    agent_responses = state.get("agent_responses", [])
    
    if status == "SANCTIONED":
        pdf_url = state.get("sanction_pdf_url", "")
        final_response = f"""
🎉 **Congratulations! Your Loan Application is APPROVED!**

Here's what happened during processing:

{chr(10).join(agent_responses)}

---
📥 **Download your Sanction Letter**: {pdf_url}
💰 Your loan will be disbursed within 24-48 hours.

Thank you for choosing us for your financial needs!
"""
    else:
        error = state.get("error_message", "Application could not be processed")
        final_response = f"""
We regret to inform you that your loan application was not approved.

**Reason**: {error}

Here's what was checked:

{chr(10).join(agent_responses)}

---
Please feel free to apply again or contact our support team for assistance.
"""
    
    return {
        "final_response": final_response,
        "processing_complete": True,
        "current_agent": "master",
        "messages": [AIMessage(content=f"🤖 **Master Agent**: Application {status}")]
    }


# ============== Routing Functions ==============

def route_after_sales(state: ChatState) -> Literal["verification", "result"]:
    """Route based on sales validation result"""
    return "result" if state.get("status") == "FAIL" else "verification"


def route_after_verification(state: ChatState) -> Literal["underwriting", "result"]:
    """Route based on verification result"""
    return "result" if state.get("status") == "FAIL" else "underwriting"


def route_after_underwriting(state: ChatState) -> Literal["sanction", "result"]:
    """Route based on underwriting result"""
    return "result" if state.get("status") == "FAIL" else "sanction"


# ============== Build LangGraph ==============

def build_chat_graph() -> StateGraph:
    """
    Build the LangGraph workflow for loan processing.
    
    Workflow:
    START → Sales → Verification → Underwriting → Sanction → Result → END
                ↓           ↓              ↓
              FAIL → → → Result → → → → END
    """
    # Create graph with state schema
    graph = StateGraph(ChatState)
    
    # Add agent nodes
    graph.add_node("sales", sales_agent_node)
    graph.add_node("verification", verification_agent_node)
    graph.add_node("underwriting", underwriting_agent_node)
    graph.add_node("sanction", sanction_agent_node)
    graph.add_node("result", master_result_node)
    
    # Entry point
    graph.add_edge(START, "sales")
    
    # Conditional routing with early exit on failure
    graph.add_conditional_edges(
        "sales",
        route_after_sales,
        {"verification": "verification", "result": "result"}
    )
    
    graph.add_conditional_edges(
        "verification",
        route_after_verification,
        {"underwriting": "underwriting", "result": "result"}
    )
    
    graph.add_conditional_edges(
        "underwriting",
        route_after_underwriting,
        {"sanction": "sanction", "result": "result"}
    )
    
    # Sanction always goes to result
    graph.add_edge("sanction", "result")
    
    # Result ends the workflow
    graph.add_edge("result", END)
    
    return graph.compile()


# Create compiled graph
chat_workflow = build_chat_graph()


def run_chat_workflow(application_data: dict) -> dict:
    """
    Execute the chat-based loan processing workflow.
    
    Args:
        application_data: Complete application data from chat session
        
    Returns:
        Final state with conversational responses and processing results
    """
    # Build initial state
    initial_state: ChatState = {
        "application_id": application_data["application_id"],
        "customer_name": application_data["customer_name"],
        "mobile": application_data["mobile"],
        "pan": application_data["pan"],
        "aadhaar": application_data["aadhaar"],
        "loan_amount": application_data["loan_amount"],
        "tenure": application_data["tenure"],
        "income": application_data["income"],
        "status": "PROCESSING",
        "credit_score": 0,
        "steps": [],
        "messages": [HumanMessage(content="Process my loan application")],
        "agent_responses": ["🤖 **Master Agent**: Starting your loan application processing..."],
        "current_agent": "master",
        "sanction_pdf_url": None,
        "error_message": None,
        "final_response": "",
        "processing_complete": False
    }
    
    # Execute the workflow
    result = chat_workflow.invoke(initial_state)
    
    return result


# ============== Streaming Support ==============

async def stream_chat_workflow(application_data: dict):
    """
    Stream the workflow execution for real-time updates.
    
    Yields state updates as each agent completes processing.
    """
    initial_state: ChatState = {
        "application_id": application_data["application_id"],
        "customer_name": application_data["customer_name"],
        "mobile": application_data["mobile"],
        "pan": application_data["pan"],
        "aadhaar": application_data["aadhaar"],
        "loan_amount": application_data["loan_amount"],
        "tenure": application_data["tenure"],
        "income": application_data["income"],
        "status": "PROCESSING",
        "credit_score": 0,
        "steps": [],
        "messages": [],
        "agent_responses": [],
        "current_agent": "master",
        "sanction_pdf_url": None,
        "error_message": None,
        "final_response": "",
        "processing_complete": False
    }
    
    # Stream execution
    async for event in chat_workflow.astream(initial_state):
        yield event
