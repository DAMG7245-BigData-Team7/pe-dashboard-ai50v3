# Phase 1 Testing Guide

## Prerequisites

### 1. Install Dependencies

```bash
cd pe-dashboard-ai50-v3
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory:

```bash
# Copy example and edit
cp .env.example .env
```

Edit `.env` with your actual keys:

```
OPENAI_API_KEY=sk-your-actual-openai-key
PINECONE_API_KEY=your-actual-pinecone-key
MCP_BASE_URL=http://localhost:9000
VECTOR_DB_URL=http://localhost:6333
```

---

## Test 1: Unit Tests (Lab 12 Checkpoint)

Run all unit tests:

```bash
# From pe-dashboard-ai50-v3 directory
pytest -v tests/test_tools.py
```

**Expected Output:**
```
tests/test_tools.py::test_get_latest_structured_payload_success PASSED
tests/test_tools.py::test_get_latest_structured_payload_not_found PASSED
tests/test_tools.py::test_get_latest_structured_payload_invalid_json PASSED
tests/test_tools.py::test_rag_search_company_success PASSED
tests/test_tools.py::test_rag_search_company_missing_api_keys PASSED
tests/test_tools.py::test_rag_search_company_empty_results PASSED
tests/test_tools.py::test_report_layoff_signal_success PASSED
tests/test_tools.py::test_report_layoff_signal_multiple_signals PASSED
tests/test_tools.py::test_report_layoff_signal_creates_directory PASSED
tests/test_tools.py::test_tools_integration PASSED

========== 10 passed in X.XXs ==========
```

---

## Test 2: Individual Tool Testing

### Test Payload Tool (Mock)

Create `test_payload_manual.py`:

```python
import asyncio
from src.tools.payload_tool import get_latest_structured_payload

async def test():
    try:
        payload = await get_latest_structured_payload("anthropic")
        print(f"✅ Payload loaded: {payload.company.company_name}")
    except FileNotFoundError as e:
        print(f"⚠️  Expected error (no payload file): {e}")

asyncio.run(test())
```

Run:
```bash
python test_payload_manual.py
```

### Test RAG Search Tool

Create `test_rag_manual.py`:

```python
import asyncio
from src.tools.rag_tool import rag_search_company

async def test():
    try:
        results = await rag_search_company("anthropic", "funding rounds")
        print(f"✅ Found {len(results)} results")
        if results:
            print(f"Top result: {results[0]['text'][:100]}...")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
```

Run:
```bash
python test_rag_manual.py
```

### Test Risk Logger

Create `test_risk_manual.py`:

```python
import asyncio
from datetime import date
from src.tools.risk_logger import report_layoff_signal, LayoffSignal

async def test():
    signal = LayoffSignal(
        company_id="test_company",
        occurred_on=date(2025, 1, 15),
        description="Test layoff signal",
        source_url="https://example.com/test",
        severity="medium"
    )

    result = await report_layoff_signal(signal, log_file="data/test_signals.jsonl")
    print(f"✅ Risk signal logged: {result}")

    # Check the file
    import json
    from pathlib import Path

    log_path = Path("data/test_signals.jsonl")
    if log_path.exists():
        with open(log_path, 'r') as f:
            lines = f.readlines()
            print(f"📄 Log contains {len(lines)} entries")
            print(f"Last entry: {json.loads(lines[-1])}")

asyncio.run(test())
```

Run:
```bash
python test_risk_manual.py
```

---

## Test 3: Supervisor Agent (Lab 13 Checkpoint)

### Option A: Quick Test (Without Real Data)

The agent will fail when trying to load payloads, but you'll see the ReAct pattern:

```bash
python src/agents/supervisor_agent.py anthropic
```

**Expected Output (partial):**
```
✅ Due Diligence Supervisor Agent initialized (run_id=abc-123...)

💭 [THOUGHT] Step 1
Starting due diligence for company: anthropic

[Agent will show Thought/Action/Observation loops]
```

### Option B: With Mock Payload (Recommended)

Create a mock payload for testing:

```bash
mkdir -p data/payloads
```

Create `data/payloads/anthropic_payload.json`:

```json
{
  "company": {
    "company_name": "Anthropic",
    "company_id": "anthropic",
    "website": "https://www.anthropic.com",
    "description": "AI safety and research company",
    "founded_year": 2021,
    "hq_city": "San Francisco",
    "hq_country": "United States"
  },
  "snapshot": {
    "snapshot_date": "2025-01-01",
    "total_funding": "$7.6B",
    "total_funding_numeric": 7600.0,
    "headcount": 500
  },
  "investor_profile": {
    "total_raised": "$7.6B",
    "total_raised_numeric": 7600.0,
    "funding_rounds": []
  },
  "growth_metrics": {
    "headcount": 500,
    "office_locations": ["San Francisco", "New York"]
  },
  "visibility": {
    "news_mentions_30d": 150
  },
  "events": [],
  "funding_rounds": [],
  "leadership": [],
  "products": [],
  "disclosure_gaps": {"missing_fields": []},
  "data_sources": ["forbes", "crunchbase"],
  "extracted_at": "2025-01-01T00:00:00"
}
```

Now run the agent:

```bash
python src/agents/supervisor_agent.py anthropic
```

**Expected Full ReAct Flow:**
```
✅ Due Diligence Supervisor Agent initialized (run_id=...)

💭 [THOUGHT] Step 1
Starting due diligence for company: anthropic

🔧 [ACTION] Step 2
{
  "tool": "get_latest_structured_payload",
  "input": "anthropic"
}

👁️ [OBSERVATION] Step 3
Payload retrieved for anthropic: Anthropic, Founded: 2021, HQ: San Francisco, Total Funding: $7.6B

🔧 [ACTION] Step 4
{
  "tool": "rag_search_company",
  "input": "anthropic|layoffs OR workforce reduction"
}

👁️ [OBSERVATION] Step 5
Found 3 relevant passages for 'layoffs OR workforce reduction':
...

✅ [FINAL_ANSWER] Step 6
Based on my analysis of Anthropic...

============================================================
FINAL ANSWER:
============================================================
[Agent's summary here]
============================================================

📊 Trace Summary: {'run_id': '...', 'total_steps': 6, 'log_file': 'logs/react_traces.jsonl'}
```

---

## Test 4: Check ReAct Logs

After running the agent, check the structured logs:

```bash
# View the trace file
cat logs/react_traces.jsonl | python -m json.tool

# Or pretty print each entry
cat logs/react_traces.jsonl | while read line; do echo "$line" | python -m json.tool; echo "---"; done
```

**Expected JSON Structure:**
```json
{
  "timestamp": "2025-01-13T...",
  "run_id": "abc-123-...",
  "step": 1,
  "type": "thought",
  "content": "Starting due diligence for company: anthropic",
  "company_id": "anthropic",
  "metadata": {}
}
```

---

## Test 5: Check Risk Signal Logs

If the agent detected risks:

```bash
cat data/risk_signals.jsonl | python -m json.tool
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'src'`

**Solution:** Run from the `pe-dashboard-ai50-v3` directory:
```bash
cd pe-dashboard-ai50-v3
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python src/agents/supervisor_agent.py anthropic
```

### Issue: `OPENAI_API_KEY not found`

**Solution:** Create `.env` file with your API key:
```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
echo "PINECONE_API_KEY=your-pinecone-key" >> .env
```

### Issue: `FileNotFoundError: No payload found`

**Solution:** Either:
1. Copy payloads from Assignment 2: `cp -r ../pe-dashboard-ai50/data/payloads data/`
2. Or create mock payload as shown in Test 3, Option B above

### Issue: Pinecone connection fails

**Solution:** The RAG tool will fail gracefully if Pinecone isn't available. For testing, you can:
1. Use the unit tests (they mock Pinecone)
2. Or set up Pinecone index from Assignment 2

---

## Success Criteria

✅ **Lab 12 Complete** if:
- All 10 unit tests pass
- Tools can be imported without errors
- Risk logger creates JSONL file

✅ **Lab 13 Complete** if:
- Agent initializes without errors
- Console shows ReAct format (Thought → Action → Observation)
- `logs/react_traces.jsonl` contains structured JSON
- Agent completes workflow and returns Final Answer

---

## Next Steps

Once tests pass, you're ready for:
- **Phase 2**: MCP Server implementation
- **Phase 3**: Graph-based workflow + HITL
- **Phase 4**: Airflow + Docker deployment
