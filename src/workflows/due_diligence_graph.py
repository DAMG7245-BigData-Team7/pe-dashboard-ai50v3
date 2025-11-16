"""
Lab 17 — Graph-based Supervisory Workflow using LangGraph

Implements a due diligence workflow with the following nodes:
1. Planner: Constructs plan of actions
2. Data Generator: Invokes MCP dashboard tools
3. Evaluator: Scores dashboards per rubric
4. Risk Detector: Branches to HITL if keywords found

Uses LangGraph StateGraph for orchestration.
"""

import asyncio
from typing import TypedDict, Annotated, Literal
from datetime import datetime
import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.planner_agent import plan_due_diligence
from src.agents.evaluation_agent import evaluate_dashboards
from src.agents.supervisor_agent import MCPClient, get_mcp_client
from src.utils.react_logger import ReActLogger


# ============================================================
# State Definition
# ============================================================

class DueDiligenceState(TypedDict):
    """State schema for due diligence workflow"""
    company_id: str
    run_id: str

    # Plan
    plan: dict | None

    # Generated dashboards
    structured_dashboard: str | None
    rag_dashboard: str | None

    # Evaluation
    evaluation_result: dict | None

    # Risk detection
    risk_detected: bool
    risk_keywords: list[str]

    # HITL
    hitl_required: bool
    hitl_approved: bool | None

    # Final output
    final_decision: str | None

    # Metadata
    execution_path: list[str]
    errors: list[str]


# ============================================================
# Node Functions
# ============================================================

def planner_node(state: DueDiligenceState) -> DueDiligenceState:
    """
    Node 1: Planner
    Constructs a plan of actions for due diligence
    """
    logger = ReActLogger(run_id=state["run_id"])
    logger.log_thought(
        f"Planning due diligence workflow for {state['company_id']}",
        company_id=state["company_id"]
    )

    try:
        plan = plan_due_diligence(state["company_id"])
        logger.log_observation(
            f"Plan created with {len(plan.get('steps', []))} steps",
            company_id=state["company_id"]
        )

        state["plan"] = plan
        state["execution_path"].append("planner")

    except Exception as e:
        state["errors"].append(f"Planner error: {str(e)}")
        logger.log_observation(f"Error in planner: {str(e)}", company_id=state["company_id"])

    return state


def data_generator_node(state: DueDiligenceState) -> DueDiligenceState:
    """
    Node 2: Data Generator
    Invokes MCP dashboard tools to generate dashboards
    """
    logger = ReActLogger(run_id=state["run_id"])
    logger.log_thought(
        "Generating dashboards via MCP tools",
        company_id=state["company_id"]
    )

    try:
        mcp = get_mcp_client()

        # Generate structured dashboard
        logger.log_action(
            "generate_structured_dashboard",
            {"company_id": state["company_id"]},
            company_id=state["company_id"]
        )

        structured_result = asyncio.run(mcp.call_tool(
            "generate_structured_dashboard",
            {"company_id": state["company_id"]}
        ))

        state["structured_dashboard"] = structured_result.get("markdown", "")
        logger.log_observation(
            f"Structured dashboard generated ({len(state['structured_dashboard'])} chars)",
            company_id=state["company_id"]
        )

        # Generate RAG dashboard
        logger.log_action(
            "generate_rag_dashboard",
            {"company_id": state["company_id"]},
            company_id=state["company_id"]
        )

        rag_result = asyncio.run(mcp.call_tool(
            "generate_rag_dashboard",
            {"company_id": state["company_id"]}
        ))

        state["rag_dashboard"] = rag_result.get("markdown", "")
        logger.log_observation(
            f"RAG dashboard generated ({len(state['rag_dashboard'])} chars)",
            company_id=state["company_id"]
        )

        state["execution_path"].append("data_generator")

    except Exception as e:
        # Fallback to stub dashboards if MCP fails
        state["errors"].append(f"Data generator error: {str(e)}")
        state["structured_dashboard"] = "# Structured Dashboard (stub - MCP unavailable)"
        state["rag_dashboard"] = "# RAG Dashboard (stub - MCP unavailable)"
        logger.log_observation(
            f"MCP unavailable, using stub dashboards: {str(e)}",
            company_id=state["company_id"]
        )
        state["execution_path"].append("data_generator_fallback")

    return state


def evaluator_node(state: DueDiligenceState) -> DueDiligenceState:
    """
    Node 3: Evaluator
    Scores dashboards per rubric

    Rubric dimensions:
    - factual: Factual accuracy
    - schema: Schema compliance
    - provenance: Source attribution
    - hallucination: Hallucination risk
    - readability: Readability score
    """
    logger = ReActLogger(run_id=state["run_id"])
    logger.log_thought(
        "Evaluating dashboards against PE rubric",
        company_id=state["company_id"]
    )

    try:
        evaluation = evaluate_dashboards(
            state.get("rag_dashboard", ""),
            state.get("structured_dashboard", "")
        )

        state["evaluation_result"] = evaluation

        logger.log_observation(
            f"Evaluation complete. Winner: {evaluation.get('winner', 'unknown')}",
            company_id=state["company_id"],
            metadata={"scores": evaluation.get("scores", {})}
        )

        state["execution_path"].append("evaluator")

    except Exception as e:
        state["errors"].append(f"Evaluator error: {str(e)}")
        logger.log_observation(f"Error in evaluator: {str(e)}", company_id=state["company_id"])

    return state


def risk_detector_node(state: DueDiligenceState) -> DueDiligenceState:
    """
    Node 4: Risk Detector
    Scans dashboards for risk keywords and determines if HITL is needed

    Risk keywords: layoff, breach, lawsuit, fraud, bankruptcy, controversy
    """
    logger = ReActLogger(run_id=state["run_id"])
    logger.log_thought(
        "Scanning for risk signals in dashboards",
        company_id=state["company_id"]
    )

    risk_keywords = [
        "layoff", "layoffs", "workforce reduction",
        "breach", "data breach", "security breach",
        "lawsuit", "litigation",
        "fraud", "fraudulent",
        "bankruptcy", "chapter 11",
        "controversy", "controversial"
    ]

    # Check both dashboards for risk keywords
    structured_text = state.get("structured_dashboard", "").lower()
    rag_text = state.get("rag_dashboard", "").lower()
    combined_text = structured_text + " " + rag_text

    detected_keywords = []
    for keyword in risk_keywords:
        if keyword in combined_text:
            detected_keywords.append(keyword)

    state["risk_detected"] = len(detected_keywords) > 0
    state["risk_keywords"] = detected_keywords
    state["hitl_required"] = state["risk_detected"]

    if state["risk_detected"]:
        logger.log_observation(
            f"⚠️  RISK DETECTED: Found {len(detected_keywords)} risk keywords: {detected_keywords}",
            company_id=state["company_id"],
            metadata={"keywords": detected_keywords}
        )
    else:
        logger.log_observation(
            "✅ No risk signals detected. Auto-approval path.",
            company_id=state["company_id"]
        )

    state["execution_path"].append("risk_detector")

    return state


def hitl_node(state: DueDiligenceState) -> DueDiligenceState:
    """
    Node 5: Human-in-the-Loop (HITL)
    Pauses workflow for human approval when risks are detected

    Lab 18: Implements actual CLI pause with input() prompt
    """
    import os

    logger = ReActLogger(run_id=state["run_id"])
    logger.log_thought(
        "⏸️  HITL checkpoint - Human approval required",
        company_id=state["company_id"]
    )

    print("\n" + "="*60)
    print("🚨 HUMAN-IN-THE-LOOP CHECKPOINT")
    print("="*60)
    print(f"Company: {state['company_id']}")
    print(f"Run ID: {state['run_id']}")
    print(f"Risk Keywords Detected: {', '.join(state['risk_keywords'])}")
    print("="*60)

    # Check if we should use interactive mode
    # Set HITL_AUTO_APPROVE=true to skip interactive input (for testing)
    auto_approve = os.getenv("HITL_AUTO_APPROVE", "false").lower() == "true"

    if auto_approve:
        print("\n[AUTO-APPROVE MODE] Automatically approving for testing...")
        print("(Set HITL_AUTO_APPROVE=false for interactive mode)\n")
        state["hitl_approved"] = True
    else:
        # Lab 18: Actual CLI pause implementation
        print("\n⏸️  WORKFLOW PAUSED - Awaiting human decision...")
        print("\nRisk Summary:")
        for idx, keyword in enumerate(state['risk_keywords'], 1):
            print(f"  {idx}. {keyword.upper()}")

        print("\nPlease review the dashboard content and decide:")
        while True:
            response = input("\n👤 Approve this company? (yes/no/details): ").strip().lower()

            if response in ['yes', 'y']:
                state["hitl_approved"] = True
                print("\n✅ APPROVED - Workflow will continue")
                break
            elif response in ['no', 'n']:
                state["hitl_approved"] = False
                print("\n❌ REJECTED - Workflow will mark as rejected")
                break
            elif response in ['details', 'd']:
                print("\n📊 Dashboard Preview:")
                print("-" * 60)
                structured = state.get("structured_dashboard", "")
                if structured:
                    # Show first 500 chars of structured dashboard
                    preview = structured[:500]
                    print(preview)
                    if len(structured) > 500:
                        print(f"\n... ({len(structured) - 500} more characters)")
                else:
                    print("No dashboard available")
                print("-" * 60)
            else:
                print("⚠️  Invalid input. Please enter 'yes', 'no', or 'details'")

    logger.log_observation(
        f"HITL decision: {'APPROVED' if state['hitl_approved'] else 'REJECTED'}",
        company_id=state["company_id"],
        metadata={"approved": state["hitl_approved"], "risk_keywords": state["risk_keywords"]}
    )

    state["execution_path"].append("hitl")

    return state


def auto_approve_node(state: DueDiligenceState) -> DueDiligenceState:
    """
    Node 6: Auto-Approve
    Automatically approves when no risks detected
    """
    logger = ReActLogger(run_id=state["run_id"])
    logger.log_observation(
        "✅ Auto-approved (no risks detected)",
        company_id=state["company_id"]
    )

    state["hitl_approved"] = True
    state["execution_path"].append("auto_approve")

    return state


def final_decision_node(state: DueDiligenceState) -> DueDiligenceState:
    """
    Node 7: Final Decision
    Summarizes workflow results and makes final recommendation
    """
    logger = ReActLogger(run_id=state["run_id"])

    evaluation_result = state.get("evaluation_result") or {}
    decision = {
        "company_id": state["company_id"],
        "run_id": state["run_id"],
        "timestamp": datetime.utcnow().isoformat(),
        "execution_path": state["execution_path"],
        "risk_detected": state["risk_detected"],
        "risk_keywords": state["risk_keywords"],
        "hitl_required": state["hitl_required"],
        "hitl_approved": state["hitl_approved"],
        "evaluation_winner": evaluation_result.get("winner", "unknown"),
        "recommendation": "APPROVED" if state["hitl_approved"] else "REJECTED",
        "errors": state["errors"]
    }

    state["final_decision"] = json.dumps(decision, indent=2)

    logger.log_final_answer(
        f"Workflow complete. Decision: {decision['recommendation']}",
        company_id=state["company_id"],
        metadata=decision
    )

    state["execution_path"].append("final_decision")

    return state


# ============================================================
# Routing Logic
# ============================================================

def route_after_risk_detection(state: DueDiligenceState) -> Literal["hitl", "auto_approve"]:
    """
    Router: Determines whether to branch to HITL or auto-approve
    Based on risk detection results
    """
    if state["risk_detected"]:
        return "hitl"
    else:
        return "auto_approve"


# ============================================================
# Graph Construction
# ============================================================

def create_due_diligence_graph() -> StateGraph:
    """
    Construct the LangGraph workflow

    Flow:
    START → Planner → Data Generator → Evaluator → Risk Detector
                                                          ↓
                                              [Risk Detected?]
                                              ↙                ↘
                                          HITL              Auto-Approve
                                              ↘                ↙
                                              Final Decision → END
    """
    workflow = StateGraph(DueDiligenceState)

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("data_generator", data_generator_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("risk_detector", risk_detector_node)
    workflow.add_node("hitl", hitl_node)
    workflow.add_node("auto_approve", auto_approve_node)
    workflow.add_node("final_decision", final_decision_node)

    # Define edges (linear flow until risk detection)
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "data_generator")
    workflow.add_edge("data_generator", "evaluator")
    workflow.add_edge("evaluator", "risk_detector")

    # Conditional branching after risk detection
    workflow.add_conditional_edges(
        "risk_detector",
        route_after_risk_detection,
        {
            "hitl": "hitl",
            "auto_approve": "auto_approve"
        }
    )

    # Both branches converge to final decision
    workflow.add_edge("hitl", "final_decision")
    workflow.add_edge("auto_approve", "final_decision")
    workflow.add_edge("final_decision", END)

    return workflow


def compile_workflow():
    """Compile the workflow with memory checkpointing"""
    graph = create_due_diligence_graph()
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# ============================================================
# CLI Interface
# ============================================================

def run_workflow(company_id: str, run_id: str | None = None):
    """
    Execute the due diligence workflow for a company

    Args:
        company_id: Company identifier
        run_id: Optional run ID for correlation

    Returns:
        Final state with decision
    """
    from uuid import uuid4

    run_id = run_id or str(uuid4())

    print("\n" + "="*60)
    print(f"🚀 STARTING DUE DILIGENCE WORKFLOW")
    print("="*60)
    print(f"Company ID: {company_id}")
    print(f"Run ID: {run_id}")
    print("="*60 + "\n")

    # Initialize state
    initial_state: DueDiligenceState = {
        "company_id": company_id,
        "run_id": run_id,
        "plan": None,
        "structured_dashboard": None,
        "rag_dashboard": None,
        "evaluation_result": None,
        "risk_detected": False,
        "risk_keywords": [],
        "hitl_required": False,
        "hitl_approved": None,
        "final_decision": None,
        "execution_path": [],
        "errors": []
    }

    # Compile and run workflow
    app = compile_workflow()

    config = {"configurable": {"thread_id": run_id}}

    final_state = None
    for state in app.stream(initial_state, config):
        # Print intermediate state transitions
        node_name = list(state.keys())[0]
        print(f"\n📍 Completed node: {node_name}")
        final_state = state[node_name]

    print("\n" + "="*60)
    print("✅ WORKFLOW COMPLETE")
    print("="*60)
    print(f"Execution Path: {' → '.join(final_state['execution_path'])}")
    print(f"Branch Taken: {'HITL' if final_state['hitl_required'] else 'Auto-Approve'}")
    print("="*60 + "\n")

    if final_state["final_decision"]:
        print("📊 Final Decision:")
        print(final_state["final_decision"])

    return final_state


if __name__ == "__main__":
    import sys

    company_id = sys.argv[1] if len(sys.argv) > 1 else "anthropic"
    run_id = sys.argv[2] if len(sys.argv) > 2 else None

    final_state = run_workflow(company_id, run_id)

    print(f"\n✅ Lab 17 Checkpoint: Workflow executed, branch taken = {'HITL' if final_state['hitl_required'] else 'Auto-Approve'}")
