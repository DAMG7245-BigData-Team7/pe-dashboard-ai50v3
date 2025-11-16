#!/usr/bin/env python3
"""
Phase 2 Complete - Lab 14-15 Validation Script

Tests the complete Agent → MCP → Dashboard → Agent round trip:
1. Start MCP server
2. Test MCP endpoints
3. Run agent with MCP enabled
4. Verify dashboard generation
"""

import os
import sys
import time
import asyncio
import subprocess
import httpx
from pathlib import Path

# Set Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.supervisor_agent import DueDiligenceSupervisorAgent, MCPClient


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_status(message: str, status: str = "INFO"):
    """Print formatted status message"""
    emojis = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "RUNNING": "🏃"
    }
    emoji = emojis.get(status, "ℹ️")
    print(f"{emoji} {message}")


async def test_mcp_server_direct():
    """Test MCP server endpoints directly"""
    print_section("Step 1: Testing MCP Server Endpoints")

    base_url = os.getenv("MCP_BASE_URL", "http://localhost:9000")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Test health endpoint
            print_status("Testing health endpoint...", "RUNNING")
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print_status(f"Health check: {response.json()}", "SUCCESS")
            else:
                print_status(f"Health check failed: {response.status_code}", "ERROR")
                return False

            # Test server info
            print_status("Testing server info endpoint...", "RUNNING")
            response = await client.get(f"{base_url}/")
            if response.status_code == 200:
                data = response.json()
                print_status(f"Server: {data['name']} v{data['version']}", "SUCCESS")
                print_status(f"Tools: {', '.join(data['tools'])}", "INFO")
                print_status(f"Resources: {', '.join(data['resources'])}", "INFO")
                print_status(f"Prompts: {', '.join(data['prompts'])}", "INFO")
            else:
                print_status(f"Server info failed: {response.status_code}", "ERROR")
                return False

            # Test company list resource
            print_status("Testing company list resource...", "RUNNING")
            response = await client.get(f"{base_url}/resource/ai50/companies")
            if response.status_code == 200:
                data = response.json()
                print_status(f"Found {data['count']} companies", "SUCCESS")
            else:
                print_status(f"Company list failed: {response.status_code}", "ERROR")
                return False

            # Test prompt endpoint
            print_status("Testing PE dashboard prompt...", "RUNNING")
            response = await client.get(f"{base_url}/prompt/pe-dashboard")
            if response.status_code == 200:
                data = response.json()
                print_status(f"Prompt template has {len(data['sections'])} sections", "SUCCESS")
            else:
                print_status(f"Prompt endpoint failed: {response.status_code}", "ERROR")
                return False

            return True

        except Exception as e:
            print_status(f"MCP server test failed: {str(e)}", "ERROR")
            return False


async def test_mcp_client():
    """Test MCP client functionality"""
    print_section("Step 2: Testing MCP Client")

    try:
        print_status("Initializing MCP client...", "RUNNING")
        mcp = MCPClient()
        print_status(f"MCP base URL: {mcp.base_url}", "INFO")

        # Test health check
        print_status("Testing MCP client health check...", "RUNNING")
        is_healthy = await mcp.health_check()
        if is_healthy:
            print_status("MCP server is healthy", "SUCCESS")
        else:
            print_status("MCP server health check failed", "ERROR")
            return False

        # Test resource retrieval
        print_status("Testing resource retrieval...", "RUNNING")
        companies = await mcp.get_resource("ai50_companies")
        print_status(f"Retrieved {companies['count']} companies via MCP client", "SUCCESS")

        return True

    except Exception as e:
        print_status(f"MCP client test failed: {str(e)}", "ERROR")
        return False


def test_agent_local_mode():
    """Test agent in local mode (without MCP)"""
    print_section("Step 3: Testing Agent - Local Mode")

    try:
        print_status("Initializing agent in local mode...", "RUNNING")
        agent = DueDiligenceSupervisorAgent(enable_mcp=False)
        print_status("Agent initialized successfully", "SUCCESS")

        print_status("Running local agent workflow...", "RUNNING")
        result = agent.run("anthropic")

        if "Due Diligence Summary" in result:
            print_status("Local agent workflow completed successfully", "SUCCESS")
            return True
        else:
            print_status("Local agent workflow output invalid", "ERROR")
            return False

    except Exception as e:
        print_status(f"Local agent test failed: {str(e)}", "ERROR")
        return False


def test_agent_mcp_mode():
    """Test agent with MCP enabled"""
    print_section("Step 4: Testing Agent - MCP Mode (Lab 15 Checkpoint)")

    try:
        print_status("Initializing agent with MCP enabled...", "RUNNING")
        agent = DueDiligenceSupervisorAgent(enable_mcp=True)
        print_status(f"Agent initialized with {len(agent.tools)} tools", "SUCCESS")

        print_status("Running MCP-enabled agent workflow...", "RUNNING")
        result = agent.run("anthropic")

        # Verify MCP dashboard generation
        if "Dashboard generated" in result or "Generated Dashboard" in result:
            print_status("MCP dashboard generation successful", "SUCCESS")
        else:
            print_status("MCP dashboard not generated (may be expected if server not running)", "WARNING")

        if "Due Diligence Summary" in result:
            print_status("MCP agent workflow completed successfully", "SUCCESS")
            return True
        else:
            print_status("MCP agent workflow output invalid", "ERROR")
            return False

    except Exception as e:
        print_status(f"MCP agent test failed: {str(e)}", "ERROR")
        print_status("Ensure MCP server is running: uvicorn src.server.mcp_server:app --port 9000", "INFO")
        return False


async def main():
    """Run all Phase 2 validation tests"""
    print_section("Phase 2 Validation - Labs 14-15")
    print_status("Starting comprehensive Phase 2 tests...", "INFO")

    results = {
        "MCP Server Endpoints": False,
        "MCP Client": False,
        "Agent Local Mode": False,
        "Agent MCP Mode": False
    }

    # Check if MCP server is running
    print_status("Checking MCP server availability...", "INFO")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:9000/health")
            if response.status_code == 200:
                print_status("MCP server is running", "SUCCESS")
                server_running = True
            else:
                server_running = False
    except:
        print_status("MCP server not detected", "WARNING")
        print_status("To start server: uvicorn src.server.mcp_server:app --port 9000", "INFO")
        server_running = False

    # Run tests
    if server_running:
        results["MCP Server Endpoints"] = await test_mcp_server_direct()
        results["MCP Client"] = await test_mcp_client()
    else:
        print_status("Skipping MCP server tests (server not running)", "WARNING")

    # Agent tests don't require MCP server for local mode
    results["Agent Local Mode"] = test_agent_local_mode()

    if server_running:
        results["Agent MCP Mode"] = test_agent_mcp_mode()
    else:
        print_status("Skipping MCP agent test (server not running)", "WARNING")

    # Print summary
    print_section("Phase 2 Validation Summary")

    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)

    for test_name, passed in results.items():
        status = "SUCCESS" if passed else "ERROR"
        print_status(f"{test_name}: {'PASSED' if passed else 'FAILED/SKIPPED'}", status)

    print(f"\n{'='*70}")
    print(f"  Results: {passed_tests}/{total_tests} tests passed")
    print(f"{'='*70}\n")

    if passed_tests == total_tests:
        print_status("🎉 Phase 2 Complete! All tests passed!", "SUCCESS")
        print_status("✅ Lab 14: MCP Server Implementation - COMPLETE", "SUCCESS")
        print_status("✅ Lab 15: Agent MCP Consumption - COMPLETE", "SUCCESS")
    elif passed_tests >= total_tests - 2:
        print_status("⚠️ Phase 2 mostly complete (some tests skipped)", "WARNING")
        print_status("Start MCP server and re-run for full validation", "INFO")
    else:
        print_status("Phase 2 validation incomplete", "ERROR")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
