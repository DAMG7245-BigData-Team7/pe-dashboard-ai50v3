# ReAct Pattern Trace Example

## Overview

This document demonstrates the ReAct (Reasoning + Acting) pattern implementation for PE due diligence workflows. The pattern follows a structured Thought → Action → Observation cycle, with all steps logged in structured JSON format.

## Pattern Components

### 1. Thought
Agent reasoning and planning steps (💭)

### 2. Action
Tool invocations and operations (🔧)

### 3. Observation
Results and feedback from actions (👁️)

### 4. Final Answer
Conclusion and summary (✅)

---

## Example Trace: Due Diligence for Anthropic

**Correlation IDs:**
- `run_id`: `demo-run-12345`
- `company_id`: `anthropic`

### Step-by-Step Execution

#### Step 1: Initial Thought
```json
{
  "timestamp": "2025-11-16T22:07:10.871576",
  "run_id": "demo-run-12345",
  "step": 1,
  "type": "thought",
  "content": "I need to perform due diligence on Anthropic",
  "company_id": "anthropic",
  "metadata": {}
}
```

#### Step 2: Action - Get Payload
```json
{
  "timestamp": "2025-11-16T22:07:10.871918",
  "run_id": "demo-run-12345",
  "step": 2,
  "type": "action",
  "content": {
    "tool": "get_payload",
    "input": {
      "company_id": "anthropic"
    }
  },
  "company_id": "anthropic",
  "metadata": {}
}
```

#### Step 3: Observation - Payload Retrieved
```json
{
  "timestamp": "2025-11-16T22:07:10.871964",
  "run_id": "demo-run-12345",
  "step": 3,
  "type": "observation",
  "content": "Retrieved payload: Anthropic, Founded 2021, AI Safety & Research",
  "company_id": "anthropic",
  "metadata": {}
}
```

#### Step 4: Thought - Plan Risk Analysis
```json
{
  "timestamp": "2025-11-16T22:07:10.871993",
  "run_id": "demo-run-12345",
  "step": 4,
  "type": "thought",
  "content": "Now I should search for risk signals",
  "company_id": "anthropic",
  "metadata": {}
}
```

#### Step 5: Action - Search Documents
```json
{
  "timestamp": "2025-11-16T22:07:10.872017",
  "run_id": "demo-run-12345",
  "step": 5,
  "type": "action",
  "content": {
    "tool": "search_company_docs",
    "input": {
      "query": "layoffs OR controversies"
    }
  },
  "company_id": "anthropic",
  "metadata": {}
}
```

#### Step 6: Observation - Search Results
```json
{
  "timestamp": "2025-11-16T22:07:10.872043",
  "run_id": "demo-run-12345",
  "step": 6,
  "type": "observation",
  "content": "Found 2 articles mentioning workforce optimization",
  "company_id": "anthropic",
  "metadata": {}
}
```

#### Step 7: Thought - Risk Detected
```json
{
  "timestamp": "2025-11-16T22:07:10.872064",
  "run_id": "demo-run-12345",
  "step": 7,
  "type": "thought",
  "content": "Risk detected, need to log this",
  "company_id": "anthropic",
  "metadata": {}
}
```

#### Step 8: Action - Log Risk Signal
```json
{
  "timestamp": "2025-11-16T22:07:10.872085",
  "run_id": "demo-run-12345",
  "step": 8,
  "type": "action",
  "content": {
    "tool": "log_risk_signal",
    "input": {
      "company_id": "anthropic",
      "description": "workforce optimization"
    }
  },
  "company_id": "anthropic",
  "metadata": {}
}
```

#### Step 9: Observation - Risk Logged
```json
{
  "timestamp": "2025-11-16T22:07:10.872109",
  "run_id": "demo-run-12345",
  "step": 9,
  "type": "observation",
  "content": "Risk signal logged successfully",
  "company_id": "anthropic",
  "metadata": {}
}
```

#### Step 10: Final Answer
```json
{
  "timestamp": "2025-11-16T22:07:10.872130",
  "run_id": "demo-run-12345",
  "step": 10,
  "type": "final_answer",
  "content": "Due diligence complete. Risks detected and logged.",
  "company_id": "anthropic",
  "metadata": {}
}
```

---

## Trace Summary

| Metric | Value |
|--------|-------|
| Total Steps | 10 |
| Thoughts | 3 |
| Actions | 3 |
| Observations | 3 |
| Run Duration | ~0.7ms |
| Tools Used | get_payload, search_company_docs, log_risk_signal |

## Correlation & Tracing

All log entries include:
- **run_id**: Unique identifier for this execution (`demo-run-12345`)
- **company_id**: Entity being analyzed (`anthropic`)
- **timestamp**: ISO 8601 UTC timestamp
- **step**: Sequential step number
- **metadata**: Extensible field for additional context

## Log File Location

Traces are written to: `logs/react_traces.jsonl` (newline-delimited JSON)

## Usage

```python
from src.utils.react_logger import ReActLogger

# Initialize with correlation IDs
logger = ReActLogger(run_id='custom-run-id')

# Log ReAct steps
logger.log_thought("I need to analyze...", company_id="anthropic")
logger.log_action("tool_name", {"param": "value"}, company_id="anthropic")
logger.log_observation("Tool returned...", company_id="anthropic")
logger.log_final_answer("Analysis complete", company_id="anthropic")
```

## Lab 16 Checkpoint ✅

- ✅ Thought/Action/Observation triplets logged in structured JSON
- ✅ Correlation IDs (run_id, company_id) included
- ✅ Sequential step numbering
- ✅ ISO 8601 timestamps
- ✅ JSONL format for efficient streaming/parsing
- ✅ Example trace saved to docs/REACT_TRACE_EXAMPLE.md
