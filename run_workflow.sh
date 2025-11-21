#!/bin/bash

# Run Due Diligence Workflow
# Usage: ./run_workflow.sh [company_id]
# Example: ./run_workflow.sh anthropic

COMPANY_ID=${1:-anthropic}

export PYTHONPATH=.
export HITL_AUTO_APPROVE=true

python3 src/workflows/due_diligence_graph.py "$COMPANY_ID"
