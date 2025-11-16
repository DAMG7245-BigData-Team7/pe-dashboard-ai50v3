#!/usr/bin/env python3
"""
Live MCP Server Test

Starts the MCP server and tests all endpoints with real HTTP requests.
"""

import time
import subprocess
import requests
import sys
from pathlib import Path

print("="*70)
print("LIVE MCP SERVER TEST")
print("="*70)

# Start MCP server in background
print("\n[1/6] Starting MCP server...")
server_process = subprocess.Popen(
    ["python3", "-m", "uvicorn", "src.server.mcp_server:app", "--port", "9000"],
    env={"PYTHONPATH": "."},
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=Path(__file__).parent
)

# Wait for server to start
time.sleep(3)

try:
    base_url = "http://localhost:9000"

    # Test 1: Health check
    print("\n[2/6] Testing health endpoint...")
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✅ Health check passed")

    # Test 2: Server info
    print("\n[3/6] Testing server info...")
    response = requests.get(f"{base_url}/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "PE Dashboard MCP Server"
    assert len(data["tools"]) == 2
    assert len(data["resources"]) == 1
    assert len(data["prompts"]) == 1
    print("✅ Server info passed")
    print(f"   Tools: {data['tools']}")
    print(f"   Resources: {data['resources']}")
    print(f"   Prompts: {data['prompts']}")

    # Test 3: Resource endpoint
    print("\n[4/6] Testing /resource/ai50/companies...")
    response = requests.get(f"{base_url}/resource/ai50/companies")
    assert response.status_code == 200
    data = response.json()
    assert "company_ids" in data
    assert data["count"] > 0
    print(f"✅ Resource endpoint passed ({data['count']} companies)")
    print(f"   Companies: {data['company_ids'][:5]}...")

    # Test 4: Prompt endpoint
    print("\n[5/6] Testing /prompt/pe-dashboard...")
    response = requests.get(f"{base_url}/prompt/pe-dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "pe-dashboard"
    assert len(data["sections"]) == 8
    print("✅ Prompt endpoint passed")
    print(f"   Sections: {len(data['sections'])}")

    # Test 5: Tool endpoints
    print("\n[6/6] Testing tool endpoints...")
    response = requests.post(
        f"{base_url}/tool/generate_structured_dashboard",
        json={"company_id": "anthropic"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == "anthropic"
    assert data["method"] == "structured"
    assert "markdown" in data
    print("✅ Tool endpoints passed")
    print(f"   Dashboard generated: {len(data['markdown'])} characters")

    print("\n" + "="*70)
    print("✅ ALL LIVE TESTS PASSED")
    print("="*70)
    print("\nMCP Server is fully operational!")
    print(f"Server URL: {base_url}")
    print("\nEndpoints tested:")
    print("  ✅ GET  /health")
    print("  ✅ GET  /")
    print("  ✅ GET  /resource/ai50/companies")
    print("  ✅ GET  /prompt/pe-dashboard")
    print("  ✅ POST /tool/generate_structured_dashboard")
    print("="*70)

except Exception as e:
    print(f"\n❌ Test failed: {e}")
    sys.exit(1)

finally:
    # Stop server
    print("\nStopping MCP server...")
    server_process.terminate()
    server_process.wait(timeout=5)
    print("Server stopped.")
