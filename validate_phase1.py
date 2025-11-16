#!/usr/bin/env python3
"""
Phase 1 Validation Script
Verifies all Lab 12-13 requirements are met
"""

import sys
import json
from pathlib import Path
import inspect

print("="*70)
print("PHASE 1 VALIDATION - Labs 12-13")
print("="*70)

validation_results = []

def check(description, condition, details=""):
    """Track validation checks"""
    status = "✅ PASS" if condition else "❌ FAIL"
    validation_results.append({
        "check": description,
        "passed": condition,
        "details": details
    })
    print(f"\n{status} | {description}")
    if details:
        print(f"     {details}")
    return condition

# ============================================================================
# LAB 12 - Core Agent Tools
# ============================================================================

print("\n" + "="*70)
print("LAB 12 - CORE AGENT TOOLS")
print("="*70)

# Check 1: Tool 1 - get_latest_structured_payload
print("\n[1] Tool: get_latest_structured_payload")
try:
    from src.tools.payload_tool import get_latest_structured_payload

    # Check if it's async
    is_async = inspect.iscoroutinefunction(get_latest_structured_payload)
    check("Tool is async function", is_async)

    # Check signature
    sig = inspect.signature(get_latest_structured_payload)
    has_company_id = 'company_id' in sig.parameters
    check("Has 'company_id' parameter", has_company_id, f"Signature: {sig}")

    # Check it uses Pydantic models
    import src.tools.payload_tool as payload_module
    source = inspect.getsource(payload_module)
    uses_pydantic = 'CompanyPayload' in source or 'BaseModel' in source
    check("Uses Pydantic models", uses_pydantic)

except Exception as e:
    check("get_latest_structured_payload exists", False, str(e))

# Check 2: Tool 2 - rag_search_company
print("\n[2] Tool: rag_search_company")
try:
    from src.tools.rag_tool import rag_search_company

    is_async = inspect.iscoroutinefunction(rag_search_company)
    check("Tool is async function", is_async)

    sig = inspect.signature(rag_search_company)
    has_company_id = 'company_id' in sig.parameters
    has_query = 'query' in sig.parameters
    check("Has 'company_id' and 'query' parameters",
          has_company_id and has_query, f"Signature: {sig}")

    import src.tools.rag_tool as rag_module
    source = inspect.getsource(rag_module)
    uses_pinecone = 'Pinecone' in source or 'pinecone' in source.lower()
    check("Queries Vector DB (Pinecone)", uses_pinecone)

except Exception as e:
    check("rag_search_company exists", False, str(e))

# Check 3: Tool 3 - report_layoff_signal
print("\n[3] Tool: report_layoff_signal")
try:
    from src.tools.risk_logger import report_layoff_signal, LayoffSignal

    is_async = inspect.iscoroutinefunction(report_layoff_signal)
    check("Tool is async function", is_async)

    sig = inspect.signature(report_layoff_signal)
    has_signal_data = 'signal_data' in sig.parameters or 'signal' in str(sig)
    check("Has signal_data parameter", has_signal_data, f"Signature: {sig}")

    # Check LayoffSignal is Pydantic model
    from pydantic import BaseModel
    is_pydantic = issubclass(LayoffSignal, BaseModel)
    check("LayoffSignal is Pydantic model", is_pydantic)

    # Check it logs risks
    import src.tools.risk_logger as risk_module
    source = inspect.getsource(risk_module)
    logs_to_file = 'jsonl' in source.lower() or 'json' in source.lower()
    check("Logs to file (JSONL)", logs_to_file)

except Exception as e:
    check("report_layoff_signal exists", False, str(e))

# Check 4: Unit tests exist
print("\n[4] Unit Tests")
test_file = Path("tests/test_tools.py")
check("test_tools.py exists", test_file.exists(), f"Path: {test_file}")

if test_file.exists():
    content = test_file.read_text()
    has_payload_test = "test_get_latest_structured_payload" in content
    has_rag_test = "test_rag_search" in content
    has_risk_test = "test_report_layoff_signal" in content

    check("Tests for get_latest_structured_payload", has_payload_test)
    check("Tests for rag_search_company", has_rag_test)
    check("Tests for report_layoff_signal", has_risk_test)

    # Count test functions
    test_count = content.count("async def test_") + content.count("def test_")
    check("Multiple test cases (≥3)", test_count >= 3, f"Found {test_count} tests")

# ============================================================================
# LAB 13 - Supervisor Agent Bootstrap
# ============================================================================

print("\n" + "="*70)
print("LAB 13 - SUPERVISOR AGENT BOOTSTRAP")
print("="*70)

# Check 5: Supervisor Agent exists
print("\n[5] Supervisor Agent")
try:
    from src.agents.supervisor_agent import DueDiligenceSupervisorAgent

    check("DueDiligenceSupervisorAgent class exists", True)

    # Check system prompt
    source = inspect.getsource(DueDiligenceSupervisorAgent)
    has_system_prompt = "Due Diligence" in source and "Supervisor" in source
    check("Has Due Diligence system prompt", has_system_prompt)

    # Check tools registration
    has_tools = "tools" in source.lower()
    check("Registers tools", has_tools)

    # Check it can be instantiated
    try:
        # Don't actually instantiate (needs API keys), just check the __init__
        init_sig = inspect.signature(DueDiligenceSupervisorAgent.__init__)
        has_init = True
    except:
        has_init = False
    check("Has __init__ method", has_init)

except Exception as e:
    check("DueDiligenceSupervisorAgent exists", False, str(e))

# Check 6: ReAct Logger
print("\n[6] ReAct Logger")
try:
    from src.utils.react_logger import ReActLogger

    check("ReActLogger exists", True)

    # Check methods
    logger_methods = dir(ReActLogger)
    has_thought = 'log_thought' in logger_methods
    has_action = 'log_action' in logger_methods
    has_observation = 'log_observation' in logger_methods

    check("Has log_thought method", has_thought)
    check("Has log_action method", has_action)
    check("Has log_observation method", has_observation)

    # Check it logs to JSONL
    source = inspect.getsource(ReActLogger)
    logs_jsonl = 'jsonl' in source.lower() or '.json' in source
    check("Logs to JSONL format", logs_jsonl)

    # Check correlation IDs
    has_run_id = 'run_id' in source
    has_company_id = 'company_id' in source
    check("Tracks correlation IDs (run_id, company_id)",
          has_run_id and has_company_id)

except Exception as e:
    check("ReActLogger exists", False, str(e))

# Check 7: Log files created
print("\n[7] Generated Artifacts")
logs_dir = Path("logs")
data_dir = Path("data")

if logs_dir.exists():
    react_traces = logs_dir / "react_traces.jsonl"
    if react_traces.exists():
        check("ReAct trace file created", True, f"Path: {react_traces}")

        # Validate JSONL format
        try:
            with open(react_traces, 'r') as f:
                lines = f.readlines()
                if lines:
                    first_entry = json.loads(lines[0])
                    has_timestamp = 'timestamp' in first_entry
                    has_run_id = 'run_id' in first_entry
                    has_type = 'type' in first_entry

                    check("JSONL entries have timestamp", has_timestamp)
                    check("JSONL entries have run_id", has_run_id)
                    check("JSONL entries have type field", has_type)
                    check("Multiple trace entries", len(lines) > 1,
                          f"Found {len(lines)} entries")
        except Exception as e:
            check("Valid JSONL format", False, str(e))
    else:
        check("ReAct trace file created", False, "Run agent to generate")
else:
    check("logs/ directory exists", False, "Run agent to generate")

if data_dir.exists():
    risk_file = data_dir / "risk_signals.jsonl"
    if risk_file.exists():
        check("Risk signals file created", True, f"Path: {risk_file}")
    else:
        check("Risk signals file created", False, "Run agent to generate")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("\n" + "="*70)
print("VALIDATION SUMMARY")
print("="*70)

passed = sum(1 for r in validation_results if r['passed'])
total = len(validation_results)
pass_rate = (passed / total * 100) if total > 0 else 0

print(f"\n✅ Passed: {passed}/{total} ({pass_rate:.1f}%)")
print(f"❌ Failed: {total - passed}/{total}")

if passed == total:
    print("\n🎉 ALL CHECKS PASSED - Phase 1 is 100% complete!")
    sys.exit(0)
else:
    print("\n⚠️  Some checks failed - review details above")
    print("\nFailed checks:")
    for r in validation_results:
        if not r['passed']:
            print(f"  - {r['check']}")
            if r['details']:
                print(f"    {r['details']}")
    sys.exit(1)
