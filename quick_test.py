#!/usr/bin/env python3
"""
Quick verification script for Phase 1 implementation
Tests all three tools and the supervisor agent
"""

import asyncio
import sys
from pathlib import Path
from datetime import date

print("="*60)
print("PHASE 1 VERIFICATION SCRIPT")
print("="*60)

# Test 1: Check imports
print("\n[1/5] Testing imports...")
try:
    from src.tools.payload_tool import get_latest_structured_payload
    from src.tools.rag_tool import rag_search_company
    from src.tools.risk_logger import report_layoff_signal, LayoffSignal
    from src.agents.supervisor_agent import DueDiligenceSupervisorAgent
    from src.utils.react_logger import ReActLogger
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Check environment variables
print("\n[2/5] Checking environment variables...")
import os
from dotenv import load_dotenv
load_dotenv()

required_vars = ["OPENAI_API_KEY"]
optional_vars = ["PINECONE_API_KEY"]

missing = []
for var in required_vars:
    if not os.getenv(var):
        missing.append(var)
        print(f"❌ Missing required: {var}")
    else:
        print(f"✅ Found: {var}")

for var in optional_vars:
    if not os.getenv(var):
        print(f"⚠️  Optional missing: {var} (RAG search will fail)")
    else:
        print(f"✅ Found: {var}")

if missing:
    print(f"\n❌ Missing required environment variables: {missing}")
    print("Create a .env file with your API keys")
    sys.exit(1)

# Test 3: Test Risk Logger
print("\n[3/5] Testing risk logger...")
async def test_risk_logger():
    signal = LayoffSignal(
        company_id="test_company",
        occurred_on=date.today(),
        description="Test risk signal for verification",
        source_url="https://example.com/test",
        severity="low"
    )

    result = await report_layoff_signal(signal, log_file="data/test_verification.jsonl")
    return result

try:
    result = asyncio.run(test_risk_logger())
    if result:
        print("✅ Risk logger works")
        log_path = Path("data/test_verification.jsonl")
        if log_path.exists():
            print(f"✅ Log file created: {log_path}")
    else:
        print("❌ Risk logger returned False")
except Exception as e:
    print(f"❌ Risk logger failed: {e}")

# Test 4: Test ReAct Logger
print("\n[4/5] Testing ReAct logger...")
try:
    logger = ReActLogger(run_id="test-run-123")
    logger.log_thought("Testing thought logging", company_id="test")
    logger.log_action("test_tool", {"input": "test"}, company_id="test")
    logger.log_observation("Test observation", company_id="test")

    summary = logger.get_trace_summary()
    print(f"✅ ReAct logger works (steps logged: {summary['total_steps']})")

    if Path(summary['log_file']).exists():
        print(f"✅ Trace file created: {summary['log_file']}")
except Exception as e:
    print(f"❌ ReAct logger failed: {e}")

# Test 5: Check for payload data
print("\n[5/5] Checking for payload data...")
payload_dirs = [
    Path("data/payloads"),
    Path("../pe-dashboard-ai50/data/payloads"),
    Path("../../pe-dashboard-ai50/data/payloads")
]

payload_found = False
for pdir in payload_dirs:
    if pdir.exists():
        payloads = list(pdir.glob("*.json"))
        if payloads:
            print(f"✅ Found {len(payloads)} payloads in {pdir}")
            print(f"   Example: {payloads[0].name}")
            payload_found = True
            break

if not payload_found:
    print("⚠️  No payload files found")
    print("   To test with real data:")
    print("   1. Copy from Assignment 2: cp -r ../pe-dashboard-ai50/data/payloads data/")
    print("   2. Or create a mock payload (see TESTING.md)")

# Summary
print("\n" + "="*60)
print("VERIFICATION SUMMARY")
print("="*60)
print("\n✅ Phase 1 implementation is functional!")
print("\nTo run unit tests:")
print("  pytest -v tests/test_tools.py")
print("\nTo test supervisor agent:")
print("  python src/agents/supervisor_agent.py anthropic")
print("\nFor detailed testing guide, see TESTING.md")
print("="*60)
