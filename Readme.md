# Project ORBIT — Assignment 5 Starter
## Agentification & MCP Integration for PE Dashboard (DAMG7245)

This is the starter repository for Assignment 5 — *Project ORBIT Part 2*.

You will extend your Assignment 2 PE Dashboard system with:
- A **Due Diligence Supervisor Agent**
- **Core tools** for structured payload retrieval, RAG search, and risk logging
- A **Model Context Protocol (MCP)** server exposing your dashboard generation as Tools, Prompts, and Resources
- A **graph-based workflow** implementing a Supervisory pattern with ReAct reasoning and HITL (Human-in-the-Loop) approval

---

### Quick Start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt

# Run the MCP server
python src/server/mcp_server.py

# Run the Supervisor Agent
python src/agents/supervisor_agent.py

# Run the Workflow
python src/workflows/due_diligence_graph.py