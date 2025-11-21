"""
Lab 13-15 — Supervisor Agent with LangChain ReAct Pattern + MCP Integration

Due Diligence Supervisor Agent that orchestrates tools to:
- Retrieve company payloads
- Run RAG queries
- Detect and log risks
- Generate PE dashboards
- Consume MCP server tools (Lab 15)

Uses LangChain's create_react_agent with structured ReAct logging.
"""

import os
import json
import asyncio
import httpx
from datetime import date
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

try:
    # Try new langchain structure first (v1.x)
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    AGENT_TYPE = "tool_calling"
except ImportError:
    try:
        # Fallback to older structure
        from langchain.agents import AgentExecutor, create_react_agent
        AGENT_TYPE = "react"
    except ImportError:
        AGENT_TYPE = "simple"

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.tools.payload_tool import get_latest_structured_payload
from src.tools.rag_tool import rag_search_company
from src.tools.risk_logger import report_layoff_signal, LayoffSignal
from src.utils.react_logger import ReActLogger

# Load environment
load_dotenv()


# ============================================================
# MCP Client
# ============================================================

class MCPClient:
    """Client for consuming MCP server tools"""

    def __init__(self, config_path: str = "config/mcp_config.json"):
        """Initialize MCP client with configuration"""
        self.config = self._load_config(config_path)
        self.base_url = os.getenv("MCP_BASE_URL", self.config.get("base_url", "http://localhost:9000"))
        self.enabled = self.config.get("agent_config", {}).get("enable_mcp", True)
        self.timeout = self.config.get("security", {}).get("timeout", 30)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load MCP configuration from JSON file"""
        path = Path(config_path)
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
        return {}

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool endpoint

        Args:
            tool_name: Name of the tool (e.g., 'generate_structured_dashboard')
            params: Tool parameters

        Returns:
            Tool response
        """
        if not self.enabled:
            raise ValueError("MCP is disabled in configuration")

        # Get tool endpoint from config
        tool_config = self.config.get("endpoints", {}).get("tools", {}).get(tool_name, {})
        if not tool_config:
            raise ValueError(f"Tool '{tool_name}' not found in MCP config")

        url = f"{self.base_url}{tool_config['url']}"
        method = tool_config.get("method", "POST")

        # Make HTTP request
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if method == "POST":
                response = await client.post(url, json=params)
            else:
                response = await client.get(url, params=params)

            response.raise_for_status()
            return response.json()

    async def get_resource(self, resource_name: str) -> Dict[str, Any]:
        """Get an MCP resource"""
        resource_config = self.config.get("endpoints", {}).get("resources", {}).get(resource_name, {})
        if not resource_config:
            raise ValueError(f"Resource '{resource_name}' not found in MCP config")

        url = f"{self.base_url}{resource_config['url']}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except:
            return False


# ============================================================
# Tool Wrappers using @tool decorator
# ============================================================

@tool
def get_payload(company_id: str) -> str:
    """Retrieve the latest structured payload for a company.

    Args:
        company_id: Company identifier (e.g., 'anthropic')

    Returns:
        Summary of company payload information
    """
    try:
        payload = asyncio.run(get_latest_structured_payload(company_id))
        return f"Payload retrieved for {company_id}: {payload.company.company_name}, Founded: {payload.company.founded_year}, HQ: {payload.company.hq_city}, Total Funding: {payload.snapshot.total_funding}"
    except Exception as e:
        return f"Error retrieving payload: {str(e)}"


@tool
def search_company_docs(query_input: str) -> str:
    """Search company documents for specific information using RAG.

    Args:
        query_input: Format 'company_id|query' (e.g., 'anthropic|layoffs OR workforce reduction')

    Returns:
        Relevant passages from company documents
    """
    try:
        parts = query_input.split("|", 1)
        if len(parts) != 2:
            return "Error: Input must be in format 'company_id|query'"

        company_id, query = parts
        results = asyncio.run(rag_search_company(company_id.strip(), query.strip()))

        if not results:
            return f"No results found for query '{query}' in company '{company_id}'"

        # Format results
        summary = f"Found {len(results)} relevant passages for '{query}':\n\n"
        for i, result in enumerate(results[:3], 1):  # Top 3 results
            summary += f"{i}. (Score: {result['score']:.2f}) {result['text'][:200]}...\n\n"

        return summary

    except Exception as e:
        return f"Error in RAG search: {str(e)}"


@tool
def log_risk_signal(risk_data: str) -> str:
    """Log a high-risk event (layoff, breach, etc.).

    Args:
        risk_data: Format 'company_id|description|source_url'

    Returns:
        Confirmation of risk signal logging
    """
    try:
        parts = risk_data.split("|", 2)
        if len(parts) != 3:
            return "Error: Input must be in format 'company_id|description|source_url'"

        company_id, description, source_url = parts

        signal = LayoffSignal(
            company_id=company_id.strip(),
            occurred_on=date.today(),
            description=description.strip(),
            source_url=source_url.strip(),
            severity="high"
        )

        result = asyncio.run(report_layoff_signal(signal))
        return f"Risk signal logged: {result}"

    except Exception as e:
        return f"Error logging risk signal: {str(e)}"


# ============================================================
# MCP Tool Wrappers (Lab 15)
# ============================================================

# Global MCP client instance
_mcp_client = None

def get_mcp_client() -> MCPClient:
    """Get or create MCP client singleton"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


@tool
def generate_structured_dashboard_mcp(company_id: str) -> str:
    """Generate a structured PE dashboard via MCP server.

    Args:
        company_id: Company identifier (e.g., 'anthropic')

    Returns:
        Markdown dashboard content
    """
    try:
        mcp = get_mcp_client()
        result = asyncio.run(mcp.call_tool(
            "generate_structured_dashboard",
            {"company_id": company_id}
        ))
        return f"Dashboard generated for {company_id}:\n\n{result.get('markdown', 'No content')[:500]}..."
    except Exception as e:
        return f"Error generating structured dashboard via MCP: {str(e)}"


@tool
def generate_rag_dashboard_mcp(company_id: str) -> str:
    """Generate a RAG-based PE dashboard via MCP server.

    Args:
        company_id: Company identifier (e.g., 'anthropic')

    Returns:
        Markdown dashboard content
    """
    try:
        mcp = get_mcp_client()
        result = asyncio.run(mcp.call_tool(
            "generate_rag_dashboard",
            {"company_id": company_id}
        ))
        return f"RAG Dashboard generated for {company_id}:\n\n{result.get('markdown', 'No content')[:500]}..."
    except Exception as e:
        return f"Error generating RAG dashboard via MCP: {str(e)}"


@tool
def get_company_list_mcp() -> str:
    """Get list of all Forbes AI 50 companies via MCP server.

    Returns:
        List of company IDs
    """
    try:
        mcp = get_mcp_client()
        result = asyncio.run(mcp.get_resource("ai50_companies"))
        company_ids = result.get("company_ids", [])
        return f"Found {len(company_ids)} companies: {', '.join(company_ids[:10])}..."
    except Exception as e:
        return f"Error getting company list via MCP: {str(e)}"


# ============================================================
# Supervisor Agent
# ============================================================

class DueDiligenceSupervisorAgent:
    """PE Due Diligence Supervisor Agent with MCP Support"""

    def __init__(self, model: str = "gpt-4o-mini", run_id: Optional[str] = None, enable_mcp: bool = False):
        """
        Initialize Supervisor Agent

        Args:
            model: OpenAI model to use
            run_id: Unique run identifier for logging
            enable_mcp: Whether to use MCP tools instead of local tools (Lab 15)
        """
        # Initialize LLM
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        self.llm = ChatOpenAI(model=model, temperature=0, api_key=api_key)
        self.react_logger = ReActLogger(run_id=run_id)
        self.enable_mcp = enable_mcp

        # Register tools based on mode
        if enable_mcp:
            # Use MCP tools (Lab 15)
            self.tools = [
                get_payload,
                search_company_docs,
                log_risk_signal,
                generate_structured_dashboard_mcp,
                generate_rag_dashboard_mcp,
                get_company_list_mcp
            ]
            # Check MCP server health
            mcp = get_mcp_client()
            is_healthy = asyncio.run(mcp.health_check())
            print(f"🌐 MCP Server Status: {'✅ HEALTHY' if is_healthy else '❌ UNAVAILABLE'}")
        else:
            # Use local tools only (Lab 13)
            self.tools = [get_payload, search_company_docs, log_risk_signal]

        print(f"\n✅ Due Diligence Supervisor Agent initialized (run_id={self.react_logger.run_id})\n")
        print(f"📦 Mode: {'MCP Enabled' if enable_mcp else 'Local Tools Only'}")
        print(f"📦 Registered {len(self.tools)} tools: {[t.name for t in self.tools]}\n")

    def run(self, company_id: str, task: Optional[str] = None) -> str:
        """
        Execute due diligence workflow for a company

        Demonstrates ReAct pattern manually:
        1. Thought: Plan what to do
        2. Action: Use tools
        3. Observation: Review results
        4. Final Answer: Summarize findings

        Args:
            company_id: Company identifier
            task: Optional custom task (default: standard due diligence)

        Returns:
            Final answer/summary
        """
        print(f"\n{'='*60}")
        print(f"EXECUTING DUE DILIGENCE FOR: {company_id}")
        print(f"{'='*60}\n")

        # Step 1: Thought
        thought = f"Starting due diligence for company: {company_id}"
        self.react_logger.log_thought(thought, company_id=company_id)

        # Step 2: Action - Get payload
        self.react_logger.log_action(
            "get_payload",
            {"company_id": company_id},
            company_id=company_id
        )

        payload_result = get_payload.invoke({"company_id": company_id})
        self.react_logger.log_observation(payload_result, company_id=company_id)

        # Step 3: Action - Search for risk signals
        self.react_logger.log_thought(
            "Now searching for risk signals like layoffs or controversies",
            company_id=company_id
        )

        self.react_logger.log_action(
            "search_company_docs",
            {"query_input": f"{company_id}|layoffs OR workforce reduction OR controversies"},
            company_id=company_id
        )

        search_result = search_company_docs.invoke({
            "query_input": f"{company_id}|layoffs OR workforce reduction OR controversies"
        })
        self.react_logger.log_observation(search_result, company_id=company_id)

        # Step 4: Conditional risk logging
        if "layoff" in search_result.lower() or "reduction" in search_result.lower():
            self.react_logger.log_thought(
                "Risk signals detected - logging to risk database",
                company_id=company_id
            )

            self.react_logger.log_action(
                "log_risk_signal",
                {"risk_data": f"{company_id}|Potential workforce reduction detected|https://example.com/{company_id}"},
                company_id=company_id
            )

            risk_result = log_risk_signal.invoke({
                "risk_data": f"{company_id}|Potential workforce reduction signals in RAG results|https://example.com/{company_id}"
            })
            self.react_logger.log_observation(risk_result, company_id=company_id)

        # Step 5: Generate dashboard via MCP (if enabled)
        dashboard_summary = ""
        if self.enable_mcp:
            self.react_logger.log_thought(
                "Generating structured dashboard via MCP server",
                company_id=company_id
            )

            self.react_logger.log_action(
                "generate_structured_dashboard_mcp",
                {"company_id": company_id},
                company_id=company_id
            )

            dashboard_result = generate_structured_dashboard_mcp.invoke({"company_id": company_id})
            self.react_logger.log_observation(dashboard_result, company_id=company_id)
            dashboard_summary = f"\n\n4. Generated Dashboard (via MCP): {dashboard_result[:200]}..."

        # Step 6: Final Answer
        final_answer = f"""Due Diligence Summary for {company_id}:

1. Company Data: {payload_result[:200]}...

2. Risk Analysis: {"RISKS DETECTED - Potential workforce reduction signals found" if "layoff" in search_result.lower() else "No major risk signals detected"}

3. Search Results: {search_result[:300]}...{dashboard_summary}

Recommendation: {"Review risk signals before proceeding" if "layoff" in search_result.lower() else "Proceed with standard diligence process"}
"""

        self.react_logger.log_final_answer(final_answer, company_id=company_id)

        print(f"\n{'='*60}")
        print(f"FINAL ANSWER:")
        print(f"{'='*60}")
        print(final_answer)
        print(f"{'='*60}\n")

        # Print trace summary
        summary = self.react_logger.get_trace_summary()
        print(f"📊 Trace Summary: {summary}\n")

        return final_answer


# ============================================================
# CLI Interface
# ============================================================

def main():
    """Command-line interface for Supervisor Agent"""
    import argparse

    parser = argparse.ArgumentParser(description="PE Due Diligence Supervisor Agent (Lab 13-15)")
    parser.add_argument("company_id", help="Company ID to analyze (e.g., 'anthropic')")
    parser.add_argument("--task", help="Custom task description", default=None)
    parser.add_argument("--model", help="OpenAI model", default="gpt-4o-mini")
    parser.add_argument("--mcp", action="store_true", help="Enable MCP mode (Lab 15)")

    args = parser.parse_args()

    # Initialize and run agent
    agent = DueDiligenceSupervisorAgent(model=args.model, enable_mcp=args.mcp)
    agent.run(args.company_id, args.task)


if __name__ == "__main__":
    main()