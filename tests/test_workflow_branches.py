"""
Lab 17 — Test Graph Workflow Branching

Tests that the due diligence workflow correctly branches based on risk detection:
1. No-risk path → auto-approve
2. Risk path → HITL approval
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from uuid import uuid4

# Set auto-approve mode for tests (prevents hanging on input())
os.environ["HITL_AUTO_APPROVE"] = "true"

from src.workflows.due_diligence_graph import (
    create_due_diligence_graph,
    compile_workflow,
    DueDiligenceState,
    planner_node,
    data_generator_node,
    evaluator_node,
    risk_detector_node,
    hitl_node,
    auto_approve_node,
    final_decision_node,
    route_after_risk_detection
)


# ============================================================
# Test State Initialization
# ============================================================

def create_test_state(company_id: str = "test_company") -> DueDiligenceState:
    """Create a test state with default values"""
    return {
        "company_id": company_id,
        "run_id": str(uuid4()),
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


# ============================================================
# Test Individual Nodes
# ============================================================

def test_planner_node():
    """Test that planner node creates a plan"""
    state = create_test_state("anthropic")
    result = planner_node(state)

    assert result["plan"] is not None
    assert "steps" in result["plan"]
    assert len(result["plan"]["steps"]) > 0
    assert "planner" in result["execution_path"]


def test_evaluator_node():
    """Test that evaluator scores dashboards"""
    state = create_test_state("anthropic")
    state["structured_dashboard"] = "# Test Dashboard"
    state["rag_dashboard"] = "# RAG Dashboard"

    result = evaluator_node(state)

    assert result["evaluation_result"] is not None
    assert "winner" in result["evaluation_result"]
    assert "scores" in result["evaluation_result"]
    assert "evaluator" in result["execution_path"]


def test_risk_detector_no_risk():
    """Test risk detector when no risk keywords found"""
    state = create_test_state("test_company")
    state["structured_dashboard"] = "# Clean Dashboard\nNo issues here."
    state["rag_dashboard"] = "# RAG Dashboard\nEverything is fine."

    result = risk_detector_node(state)

    assert result["risk_detected"] is False
    assert len(result["risk_keywords"]) == 0
    assert result["hitl_required"] is False
    assert "risk_detector" in result["execution_path"]


def test_risk_detector_with_risk():
    """Test risk detector when risk keywords are found"""
    state = create_test_state("risky_company")
    state["structured_dashboard"] = "# Dashboard\nCompany announced layoffs in Q3."
    state["rag_dashboard"] = "# RAG Dashboard\nData breach reported last month."

    result = risk_detector_node(state)

    assert result["risk_detected"] is True
    assert len(result["risk_keywords"]) >= 2  # Should find 'layoffs' and 'breach'
    assert "layoff" in result["risk_keywords"] or "layoffs" in result["risk_keywords"]
    assert "breach" in result["risk_keywords"] or "data breach" in result["risk_keywords"]
    assert result["hitl_required"] is True
    assert "risk_detector" in result["execution_path"]


def test_route_after_risk_detection_no_risk():
    """Test routing when no risk is detected"""
    state = create_test_state()
    state["risk_detected"] = False

    route = route_after_risk_detection(state)

    assert route == "auto_approve"


def test_route_after_risk_detection_with_risk():
    """Test routing when risk is detected"""
    state = create_test_state()
    state["risk_detected"] = True

    route = route_after_risk_detection(state)

    assert route == "hitl"


def test_auto_approve_node():
    """Test auto-approve node sets approval"""
    state = create_test_state()

    result = auto_approve_node(state)

    assert result["hitl_approved"] is True
    assert "auto_approve" in result["execution_path"]


def test_hitl_node():
    """Test HITL node (currently simulated)"""
    state = create_test_state()
    state["risk_keywords"] = ["layoffs", "breach"]

    result = hitl_node(state)

    # For now, HITL auto-approves (Lab 18 will implement real pause)
    assert result["hitl_approved"] is True
    assert "hitl" in result["execution_path"]


def test_final_decision_node_approved():
    """Test final decision when approved"""
    state = create_test_state()
    state["hitl_approved"] = True
    state["risk_detected"] = False
    state["execution_path"] = ["planner", "data_generator", "evaluator", "risk_detector", "auto_approve"]

    result = final_decision_node(state)

    assert result["final_decision"] is not None
    assert "APPROVED" in result["final_decision"]
    assert "final_decision" in result["execution_path"]


def test_final_decision_node_with_risks():
    """Test final decision when risks were detected but approved"""
    state = create_test_state()
    state["hitl_approved"] = True
    state["risk_detected"] = True
    state["risk_keywords"] = ["layoffs"]
    state["execution_path"] = ["planner", "data_generator", "evaluator", "risk_detector", "hitl"]

    result = final_decision_node(state)

    assert result["final_decision"] is not None
    assert "APPROVED" in result["final_decision"]
    assert "final_decision" in result["execution_path"]


# ============================================================
# Test Full Workflow Branches
# ============================================================

@patch('src.workflows.due_diligence_graph.get_mcp_client')
def test_workflow_no_risk_branch(mock_mcp_client):
    """
    Lab 17 Checkpoint Test 1: No-risk path

    Verify that when no risk keywords are found, workflow takes auto-approve path:
    Planner → Data Generator → Evaluator → Risk Detector → Auto-Approve → Final Decision
    """
    # Mock MCP client to return clean dashboards (async function)
    async def mock_call_tool(tool_name, params):
        return {"markdown": "# Clean Dashboard\nNo issues."}

    mock_client = MagicMock()
    mock_client.call_tool = mock_call_tool
    mock_mcp_client.return_value = mock_client

    # Create initial state
    initial_state = create_test_state("clean_company")

    # Compile and run workflow
    app = compile_workflow()
    config = {"configurable": {"thread_id": initial_state["run_id"]}}

    final_state = None
    for state in app.stream(initial_state, config):
        node_name = list(state.keys())[0]
        final_state = state[node_name]

    # Assertions
    assert final_state is not None
    assert "auto_approve" in final_state["execution_path"]
    assert "hitl" not in final_state["execution_path"]
    assert final_state["risk_detected"] is False
    assert final_state["hitl_approved"] is True
    assert "APPROVED" in final_state["final_decision"]

    print(f"✅ No-risk branch test passed. Path: {' → '.join(final_state['execution_path'])}")


@patch('src.workflows.due_diligence_graph.get_mcp_client')
def test_workflow_risk_branch(mock_mcp_client):
    """
    Lab 17 Checkpoint Test 2: Risk path

    Verify that when risk keywords are found, workflow takes HITL path:
    Planner → Data Generator → Evaluator → Risk Detector → HITL → Final Decision
    """
    # Mock MCP client to return dashboards with risk keywords (async function)
    async def mock_call_tool(tool_name, params):
        if tool_name == "generate_structured_dashboard":
            return {"markdown": "# Dashboard\nCompany announced layoffs in Q3."}
        elif tool_name == "generate_rag_dashboard":
            return {"markdown": "# RAG Dashboard\nData breach reported last month."}
        return {"markdown": "# Dashboard"}

    mock_client = MagicMock()
    mock_client.call_tool = mock_call_tool
    mock_mcp_client.return_value = mock_client

    # Create initial state
    initial_state = create_test_state("risky_company")

    # Compile and run workflow
    app = compile_workflow()
    config = {"configurable": {"thread_id": initial_state["run_id"]}}

    final_state = None
    for state in app.stream(initial_state, config):
        node_name = list(state.keys())[0]
        final_state = state[node_name]

    # Assertions
    assert final_state is not None
    assert "hitl" in final_state["execution_path"]
    assert "auto_approve" not in final_state["execution_path"]
    assert final_state["risk_detected"] is True
    assert len(final_state["risk_keywords"]) > 0
    assert final_state["hitl_required"] is True
    assert final_state["hitl_approved"] is True  # Simulated approval
    assert "APPROVED" in final_state["final_decision"]

    print(f"✅ Risk branch test passed. Path: {' → '.join(final_state['execution_path'])}")
    print(f"   Risk keywords detected: {final_state['risk_keywords']}")


@patch('src.workflows.due_diligence_graph.get_mcp_client')
def test_workflow_mcp_failure_fallback(mock_mcp_client):
    """Test that workflow handles MCP failures gracefully"""
    # Mock MCP client to raise exception (async function)
    async def mock_call_tool_error(tool_name, params):
        raise Exception("MCP server unavailable")

    mock_client = MagicMock()
    mock_client.call_tool = mock_call_tool_error
    mock_mcp_client.return_value = mock_client

    initial_state = create_test_state("test_company")

    app = compile_workflow()
    config = {"configurable": {"thread_id": initial_state["run_id"]}}

    final_state = None
    for state in app.stream(initial_state, config):
        node_name = list(state.keys())[0]
        final_state = state[node_name]

    # Should complete with fallback dashboards
    assert final_state is not None
    assert "data_generator_fallback" in final_state["execution_path"]
    assert len(final_state["errors"]) > 0
    assert "APPROVED" in final_state["final_decision"]

    print(f"✅ MCP fallback test passed. Errors: {final_state['errors']}")


# ============================================================
# Test Graph Structure
# ============================================================

def test_graph_has_all_nodes():
    """Test that graph contains all required nodes"""
    workflow = create_due_diligence_graph()

    # LangGraph doesn't expose nodes easily, so we compile and check
    app = compile_workflow()

    # Should compile without errors
    assert app is not None


def test_graph_conditional_routing():
    """Test that conditional routing is configured correctly"""
    # Test the router function directly
    no_risk_state = create_test_state()
    no_risk_state["risk_detected"] = False

    risk_state = create_test_state()
    risk_state["risk_detected"] = True

    assert route_after_risk_detection(no_risk_state) == "auto_approve"
    assert route_after_risk_detection(risk_state) == "hitl"


# ============================================================
# Integration Test
# ============================================================

@patch('src.workflows.due_diligence_graph.get_mcp_client')
def test_full_workflow_integration(mock_mcp_client):
    """
    Integration test: Run workflow with both branches and verify complete execution
    """
    # Test 1: No risk
    async def mock_call_tool_clean(tool_name, params):
        return {"markdown": "# Dashboard\nAll good."}

    mock_client = MagicMock()
    mock_client.call_tool = mock_call_tool_clean
    mock_mcp_client.return_value = mock_client

    state1 = create_test_state("clean_company")
    app = compile_workflow()
    config1 = {"configurable": {"thread_id": state1["run_id"]}}

    final_state1 = None
    for state in app.stream(state1, config1):
        final_state1 = state[list(state.keys())[0]]

    assert "auto_approve" in final_state1["execution_path"]

    # Test 2: With risk (modify mock to return risky content)
    async def mock_call_tool_risky(tool_name, params):
        return {"markdown": "# Dashboard\nLayoffs announced. Lawsuit filed."}

    mock_client.call_tool = mock_call_tool_risky

    state2 = create_test_state("risky_company")
    config2 = {"configurable": {"thread_id": state2["run_id"]}}

    final_state2 = None
    for state in app.stream(state2, config2):
        final_state2 = state[list(state.keys())[0]]

    assert "hitl" in final_state2["execution_path"]

    print("✅ Full integration test passed - both branches work correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
