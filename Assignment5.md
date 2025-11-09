# Assignment 5 — DAMG 7245  
## Case Study 2 — Project ORBIT (Part 2)  
### Agentification and Secure Scaling of PE Intelligence using MCP

---

## Setting

Your **PE Dashboard Factory** from Assignment 2 (Project ORBIT Part 1) successfully automated data ingestion and Markdown dashboard generation for the **Forbes AI 50**.  
That system relied on:

- Structured payloads assembled from scraped data  
- RAG (vector DB) retrieval  
- FastAPI + Streamlit app  
- Airflow for initial and daily pipelines  

However, the workflow is still **static and scheduled** — it does not reason, adapt, or coordinate multiple tools and data sources autonomously.

To take Project ORBIT to the next level, **Priya Rao (VP of Data Engineering)** wants to introduce:

- **Supervisory LLM Agents** that orchestrate complex PE due-diligence flows  
- **MCP (Model Context Protocol)** to standardize access to internal tools, prompts & resources  
- **ReAct (Reasoning + Acting)** pattern for iterative tool use  
- **Graph-based workflows** (e.g., LangGraph or WorkflowBuilder) with Human-in-the-Loop (HITL) checkpoints  

Your job is to **upgrade the PE Dashboard Factory into an Agentic Due Diligence Workflow.**

This assignment builds directly on **Assignment 2 — Project ORBIT Part 1.**

---

## Learning Outcomes

By completing this assignment, you will:

- Build specialized LLM Agents using modern frameworks (e.g., **Microsoft Agent Framework** or **LangChain v1**)  
- Design & implement a **Supervisory Agent Architecture** for multi-step task delegation  
- Implement the **Model Context Protocol (MCP)** to expose your dashboard logic as **Tools, Prompts and Resources**  
- Apply the **ReAct Pattern** (Thought → Action → Observation) for transparent reasoning  
- Build an **Agentic Workflow** with graph-based flow control & explicit planning  
- Integrate **Human-in-the-Loop (HITL)** decision points for risk verification  
- Implement **Tool Filtering** & secure access control  

---

## Phase 1 – Agent Infrastructure & Tool Definition (Labs 12 – 13)

### Lab 12 — Core Agent Tools

**Goal:** Define and expose the core tools your Due Diligence Agent will use to access Assignment 2 data.

Each tool is an `async def` Python function using **Pydantic models** for structured I/O.

**Tasks**

1. Implement `src/tools/payload_tool.py`:

```python
async def get_latest_structured_payload(company_id: str) -> Payload:
    """
    Retrieve the latest fully assembled structured payload for a company.
    Payload schema must include: company_record, events, snapshots, products, leadership, visibility.
    """

	2.	Implement src/tools/rag_tool.py:

async def rag_search_company(company_id: str, query: str) -> list[dict]:
    """
    Run retrieval-augmented search for the company and query.
    Returns [{ "text": ..., "source_url": ..., "score": ... }]
    """

	3.	Implement src/tools/risk_logger.py:

async def report_layoff_signal(signal_data: LayoffSignal) -> bool:
    """
    Log or persist a layoff / risk event.
    Destructive tool — side effects only (e.g., write to DB or log).
    """

LayoffSignal must include company_id, occurred_on, description, source_url.
	4.	Add LLM-friendly docstrings and type annotations.
	5.	(Optional) Register tools in your chosen agent framework (e.g., @tool).

Checkpoint
	•	Run python tests/test_tools.py to fetch a payload, run a RAG query, and log a risk event.

⸻

Lab 13 — Agent Bootstrap (Core Supervisor)

Goal: Instantiate the Due Diligence Supervisor Agent and verify tool usage.

Tasks
	1.	Choose framework ( Microsoft Agent Framework or LangChain v1 ).
	2.	Implement src/agents/supervisor_agent.py with system instructions:

“You are a PE Due Diligence Supervisor Agent. Use tools to retrieve payloads, run RAG queries, log risks, and generate 8-section PE dashboards.”

	3.	Register tools get_latest_structured_payload, rag_search_company, report_layoff_signal.
	4.	Driver script asks agent to evaluate funding profile and layoff risks for a company.

Checkpoint

Logs show the agent calling tools in a loop to reach its goal.

⸻

Phase 2 – Model Context Protocol (MCP) Integration (Labs 14 – 15)

Lab 14 — MCP Server Implementation

Goal: Encapsulate dashboard generation logic inside an MCP server (HTTP-based).

Tasks
	1.	Implement src/server/mcp_server.py (using FastMCP or FastAPI).
	2.	Expose:

Type	Endpoint	Description
Tool	/tool/generate_rag_dashboard	Calls RAG-based dashboard logic (Assignment 2)
Tool	/tool/generate_structured_dashboard	Calls structured payload dashboard logic
Resource	/resource/ai50/companies	Lists AI 50 company IDs
Prompt	/prompt/pe-dashboard	Returns the 8-section dashboard prompt template

	3.	Document inputs & outputs so the agent knows when to use each tool.
	4.	Test with MCP Inspector or API client.

Checkpoint:
MCP Inspector shows all Tools, Resources, and Prompts visible and callable.

⸻

Lab 15 — Agent MCP Consumption

Goal: Configure Supervisor Agent to use MCP tools as remote functions.

Tasks
	1.	Create src/server/mcp_config.json with base URL and tool list.
	2.	Connect Supervisor Agent to MCP server as a tool source.
	3.	Use tool filtering to restrict agent to dashboard/RAG tools.
	4.	Test: ask agent “Generate the latest PE dashboard for company X using MCP tools.”

Checkpoint:
Agent → MCP → dashboard → Agent response end-to-end successfully returns Markdown.

⸻

Phase 3 – Advanced Agent Implementation (Labs 16 – 18)

Lab 16 — Due Diligence Agent Refinement (ReAct Pattern)

Goal: Implement explicit ReAct loop (Thought → Action → Observation).

Tasks
	•	Log each Thought/Action/Observation triplet.
	•	Use loop structure for funding and risk evaluation.

Example Trace

Thought: Fetch structured payload
Action: get_latest_structured_payload(company_id="...")
Observation: {payload}
Thought: Search RAG for layoffs
Action: rag_search_company(...)
Observation: Found 1 article mentioning layoffs

Checkpoint:
Logs clearly show ReAct sequence.

⸻

Lab 17 — Supervisory Workflow Pattern (Graph-based)

Goal: Structure end-to-end workflow using LangGraph or WorkflowBuilder.

Workflow Nodes

Node	Purpose
Planner	Creates plan (Structured → RAG → Eval → Risk check)
Data Generation	Executes MCP tools
Evaluation	Compares dashboards via rubric (Factual, Schema, Provenance, Hallucination, Readability)
Risk Edge	Checks for keywords (layoffs, regulatory incident, data breach) → HITL if found

Checkpoint:
python src/workflows/due_diligence_graph.py prints nodes visited and branch taken.

⸻

Lab 18 — Human-in-the-Loop (HITL) Integration & Visualization

Goal: Pause workflow on risk and require human approval.

Tasks
	•	Implement HITL node that waits for CLI or HTTP approval.
	•	Record execution path (Dev UI, LangSmith or Mermaid).
	•	Save trace examples in docs/REACT_TRACE_EXAMPLE.md.

Checkpoint:
Workflow shows HITL pause and resume after approval.

⸻

Deliverables

#	Deliverable	Description
1	Updated GitHub Repo	pe-dashboard-ai50-v3 with Assignment 5 code
2	MCP Server	src/server/mcp_server.py exposing Tools/Resources/Prompts
3	Core Agent Tools	Async functions + Pydantic models
4	Agentic Workflow	Supervisor + ReAct + Graph + Conditional Risk
5	HITL Integration	Manual pause/resume for risk cases
6	Documentation	README + workflow diagram + ReAct trace
7	Demo Video (≤ 5 min)	Show workflow execution + HITL pause
8	Contribution Attestation	Team names and roles


⸻

Dashboard Format Reminder (from Assignment 2)

Dashboards must include these 8 sections (in order):
	1.	Company Overview
	2.	Business Model and GTM
	3.	Funding & Investor Profile
	4.	Growth Momentum
	5.	Visibility & Market Sentiment
	6.	Risks and Challenges
	7.	Outlook
	8.	Disclosure Gaps (bullet list of missing info)

Rules
	•	Use literal “Not disclosed.” if a field is unavailable.
	•	Never invent ARR, MRR, valuation or customer logos.
	•	Always include final Disclosure Gaps section.

⸻

Submission
	•	Repo name: pe-dashboard-ai50-v3-<teamname>
	•	Include at root: Assignment5.md, README.md, docs/, src/, and demo video link.
	•	Submit GitHub URL + video link via LMS.

⸻

Reference Materials
	•	Python AI Series handouts: Structured Outputs, Tool Calling, Agents, MCP
	•	Model Context Protocol Docs
	•	LangGraph Docs
	•	Microsoft Agent Framework Samples

⸻
