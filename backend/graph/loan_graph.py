"""
LangGraph Loan Processing Workflow

Defines the multi-step agent workflow:
START → Sales → Verification → Underwriting → Sanction → END

Each node can either pass to the next node or terminate the workflow on failure.
"""

from typing import TypedDict, Literal, Any
from langgraph.graph import StateGraph, START, END

# Import agent nodes
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.sales_node import sales_node
from agents.verification_node import verification_node
from agents.underwriting_node import underwriting_node
from agents.sanction_node import sanction_node


# ============== State Schema ==============

class LoanState(TypedDict, total=False):
    """
    Shared state schema for the loan processing workflow.
    All nodes read from and write to this state.
    """
    # Application data (input)
    application_id: int
    customer_name: str
    mobile: str
    pan: str
    aadhaar: str
    loan_amount: int
    tenure: int
    income: int
    
    # Workflow tracking
    status: str  # SUCCESS, FAIL, SANCTIONED
    credit_score: int
    steps: list[dict[str, Any]]
    sanction_pdf_url: str | None
    error_message: str | None


# ============== Router Functions ==============

def route_after_sales(state: LoanState) -> Literal["verification", "end"]:
    """
    Router function after Sales Node.
    If sales validation fails, terminate workflow.
    """
    if state.get("status") == "FAIL":
        return "end"
    return "verification"


def route_after_verification(state: LoanState) -> Literal["underwriting", "end"]:
    """
    Router function after Verification Node.
    If KYC verification fails, terminate workflow.
    """
    if state.get("status") == "FAIL":
        return "end"
    return "underwriting"


def route_after_underwriting(state: LoanState) -> Literal["sanction", "end"]:
    """
    Router function after Underwriting Node.
    If underwriting fails, terminate workflow.
    """
    if state.get("status") == "FAIL":
        return "end"
    return "sanction"


# ============== Graph Builder ==============

def build_loan_graph() -> StateGraph:
    """
    Build and compile the loan processing workflow graph.
    
    Workflow:
    START → Sales → Verification → Underwriting → Sanction → END
    
    Each node can terminate the workflow early on failure.
    
    Returns:
        Compiled StateGraph ready for invocation
    """
    # Create StateGraph with state schema
    builder = StateGraph(LoanState)
    
    # Add nodes
    builder.add_node("sales", sales_node)
    builder.add_node("verification", verification_node)
    builder.add_node("underwriting", underwriting_node)
    builder.add_node("sanction", sanction_node)
    
    # Add edge: START → Sales
    builder.add_edge(START, "sales")
    
    # Add conditional edges with routing
    builder.add_conditional_edges(
        "sales",
        route_after_sales,
        {
            "verification": "verification",
            "end": END
        }
    )
    
    builder.add_conditional_edges(
        "verification",
        route_after_verification,
        {
            "underwriting": "underwriting",
            "end": END
        }
    )
    
    builder.add_conditional_edges(
        "underwriting",
        route_after_underwriting,
        {
            "sanction": "sanction",
            "end": END
        }
    )
    
    # Add edge: Sanction → END
    builder.add_edge("sanction", END)
    
    # Compile the graph
    return builder.compile()


# Create singleton graph instance
loan_graph = build_loan_graph()


def run_loan_workflow(application_data: dict[str, Any]) -> dict[str, Any]:
    """
    Execute the loan processing workflow.
    
    Args:
        application_data: Dictionary containing application details
            - application_id: int
            - customer_name: str
            - mobile: str
            - pan: str
            - aadhaar: str
            - loan_amount: int
            - tenure: int
            - income: int
            
    Returns:
        Final workflow state containing:
            - status: Final status (SUCCESS, FAIL, SANCTIONED)
            - steps: List of step results
            - sanction_pdf_url: URL to PDF if sanctioned
            - error_message: Error message if failed
    """
    # Build initial state
    initial_state: LoanState = {
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
        "sanction_pdf_url": None,
        "error_message": None
    }
    
    # Run the workflow
    result = loan_graph.invoke(initial_state)
    
    return result
