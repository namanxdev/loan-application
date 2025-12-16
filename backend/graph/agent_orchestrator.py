# -*- coding: utf-8 -*-
"""
Agent Orchestrator - LangGraph Workflow

Orchestrates the 6-agent loan processing workflow:
1. AgentAlpha - Sales Validation
2. AgentBeta - KYC Verification
3. AgentGamma - Credit Risk Assessment
4. AgentDelta - Income Analysis
5. AgentEpsilon - Fraud Detection
6. AgentZeta - Final Sanction Decision

Supports both sync and async execution with streaming updates.
"""

from typing import TypedDict, List, Annotated, Literal, Optional, Any
from operator import add
from langgraph.graph import StateGraph, START, END

from agents.decision_agents import (
    AgentAlpha, AgentBeta, AgentGamma, AgentDelta,
    AgentEpsilon, AgentZeta, AgentResult, AgentDecision
)


class AgentState(TypedDict, total=False):
    """State passed between agents in the workflow"""
    # Application data
    application_id: int
    application_data: dict
    
    # Agent results (accumulates with each node)
    agent_results: Annotated[List[AgentResult], add]
    current_agent: str
    
    # Processing status
    status: str  # PROCESSING, FAIL, SANCTIONED, MANUAL_REVIEW
    final_decision: str
    sanction_pdf_url: Optional[str]
    
    # For streaming updates to frontend
    agent_updates: Annotated[List[dict], add]
    
    # Error tracking
    error_message: Optional[str]


# Initialize agent instances
agent_alpha = AgentAlpha()
agent_beta = AgentBeta()
agent_gamma = AgentGamma()
agent_delta = AgentDelta()
agent_epsilon = AgentEpsilon()
agent_zeta = AgentZeta()


def alpha_node(state: AgentState) -> dict:
    """
    AgentAlpha - Sales Validation
    First agent in the pipeline.
    """
    result = agent_alpha.evaluate(state["application_data"])
    
    update = {
        "agent": "AgentAlpha",
        "display_name": "Sales Validator",
        "status": "complete",
        "result": result.model_dump()
    }
    
    new_status = "FAIL" if result.decision == AgentDecision.REJECT else state.get("status", "PROCESSING")
    
    return {
        "agent_results": [result],
        "current_agent": "AgentAlpha",
        "agent_updates": [update],
        "status": new_status
    }


def beta_node(state: AgentState) -> dict:
    """
    AgentBeta - KYC Verification
    Validates PAN, Aadhaar, and other KYC documents.
    """
    result = agent_beta.evaluate(state["application_data"])
    
    update = {
        "agent": "AgentBeta",
        "display_name": "KYC Verifier",
        "status": "complete",
        "result": result.model_dump()
    }
    
    new_status = "FAIL" if result.decision == AgentDecision.REJECT else state.get("status", "PROCESSING")
    
    return {
        "agent_results": [result],
        "current_agent": "AgentBeta",
        "agent_updates": [update],
        "status": new_status
    }


def gamma_node(state: AgentState) -> dict:
    """
    AgentGamma - Credit Risk Assessment
    Evaluates credit score and EMI burden.
    """
    result = agent_gamma.evaluate(state["application_data"])
    
    update = {
        "agent": "AgentGamma",
        "display_name": "Credit Analyst",
        "status": "complete",
        "result": result.model_dump()
    }
    
    new_status = "FAIL" if result.decision == AgentDecision.REJECT else state.get("status", "PROCESSING")
    
    return {
        "agent_results": [result],
        "current_agent": "AgentGamma",
        "agent_updates": [update],
        "status": new_status
    }


def delta_node(state: AgentState) -> dict:
    """
    AgentDelta - Income Analysis
    Verifies income stability and affordability.
    """
    result = agent_delta.evaluate(state["application_data"])
    
    update = {
        "agent": "AgentDelta",
        "display_name": "Income Analyzer",
        "status": "complete",
        "result": result.model_dump()
    }
    
    new_status = "FAIL" if result.decision == AgentDecision.REJECT else state.get("status", "PROCESSING")
    
    return {
        "agent_results": [result],
        "current_agent": "AgentDelta",
        "agent_updates": [update],
        "status": new_status
    }


def epsilon_node(state: AgentState) -> dict:
    """
    AgentEpsilon - Fraud Detection
    Checks for fraud patterns and anomalies.
    """
    result = agent_epsilon.evaluate(state["application_data"])
    
    update = {
        "agent": "AgentEpsilon",
        "display_name": "Fraud Detector",
        "status": "complete",
        "result": result.model_dump()
    }
    
    new_status = "FAIL" if result.decision == AgentDecision.REJECT else state.get("status", "PROCESSING")
    
    return {
        "agent_results": [result],
        "current_agent": "AgentEpsilon",
        "agent_updates": [update],
        "status": new_status
    }


def zeta_node(state: AgentState) -> dict:
    """
    AgentZeta - Final Sanction Decision
    Aggregates all results and makes final decision.
    """
    all_results = state.get("agent_results", [])
    result = agent_zeta.evaluate(state["application_data"], all_results)
    
    # Map agent decision to application status
    final_status = {
        AgentDecision.APPROVE: "SANCTIONED",
        AgentDecision.REJECT: "REJECTED",
        AgentDecision.REVIEW: "MANUAL_REVIEW"
    }.get(result.decision, "FAIL")
    
    update = {
        "agent": "AgentZeta",
        "display_name": "Sanction Authority",
        "status": "complete",
        "result": result.model_dump(),
        "is_final": True
    }
    
    return {
        "agent_results": [result],
        "current_agent": "AgentZeta",
        "final_decision": result.decision.value,
        "status": final_status,
        "agent_updates": [update]
    }


def route_after_agent(state: AgentState) -> Literal["continue", "end"]:
    """
    Router function to determine if workflow should continue or stop.
    Stops early if any agent rejects the application.
    """
    if state.get("status") == "FAIL":
        return "end"
    return "continue"


def build_agent_graph() -> StateGraph:
    """
    Build the 6-agent workflow graph.
    
    Flow: Alpha → Beta → Gamma → Delta → Epsilon → Zeta
    With early exit if any agent rejects.
    """
    graph = StateGraph(AgentState)
    
    # Add all agent nodes
    graph.add_node("alpha", alpha_node)
    graph.add_node("beta", beta_node)
    graph.add_node("gamma", gamma_node)
    graph.add_node("delta", delta_node)
    graph.add_node("epsilon", epsilon_node)
    graph.add_node("zeta", zeta_node)
    
    # Sequential flow with early exit capability
    graph.add_edge(START, "alpha")
    graph.add_conditional_edges("alpha", route_after_agent, {"continue": "beta", "end": END})
    graph.add_conditional_edges("beta", route_after_agent, {"continue": "gamma", "end": END})
    graph.add_conditional_edges("gamma", route_after_agent, {"continue": "delta", "end": END})
    graph.add_conditional_edges("delta", route_after_agent, {"continue": "epsilon", "end": END})
    graph.add_conditional_edges("epsilon", route_after_agent, {"continue": "zeta", "end": END})
    graph.add_edge("zeta", END)
    
    return graph.compile()


# Compiled workflow graph
agent_workflow = build_agent_graph()


def run_agent_workflow(application_data: dict) -> dict:
    """
    Run the complete agent workflow synchronously.
    
    Args:
        application_data: Dictionary containing loan application details
        
    Returns:
        Final state with all agent results and decisions
    """
    initial_state: AgentState = {
        "application_id": application_data.get("application_id", 0),
        "application_data": application_data,
        "agent_results": [],
        "current_agent": "",
        "status": "PROCESSING",
        "agent_updates": [],
    }
    
    # Run the workflow
    final_state = agent_workflow.invoke(initial_state)
    
    # Build response
    return {
        "status": final_state.get("status", "FAIL"),
        "final_decision": final_state.get("final_decision", "reject"),
        "agent_results": [r.model_dump() for r in final_state.get("agent_results", [])],
        "agent_updates": final_state.get("agent_updates", []),
        "sanction_pdf_url": final_state.get("sanction_pdf_url"),
    }


async def run_agent_workflow_async(application_data: dict):
    """
    Run the agent workflow with async streaming support.
    
    Yields agent updates as they complete.
    """
    initial_state: AgentState = {
        "application_id": application_data.get("application_id", 0),
        "application_data": application_data,
        "agent_results": [],
        "current_agent": "",
        "status": "PROCESSING",
        "agent_updates": [],
    }
    
    # Stream workflow execution
    async for event in agent_workflow.astream(initial_state):
        # Extract updates from this step
        agent_updates = event.get("agent_updates", [])
        for update in agent_updates:
            yield update
    
    # Yield final result
    yield {
        "type": "complete",
        "status": event.get("status", "FAIL"),
        "final_decision": event.get("final_decision"),
    }

