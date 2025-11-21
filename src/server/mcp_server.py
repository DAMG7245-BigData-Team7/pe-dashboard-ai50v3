"""
Lab 14 — MCP Server Implementation

Model Context Protocol (MCP) server exposing dashboard generation as:
- Tools: Dashboard generation endpoints
- Resources: Company data endpoints
- Prompts: Dashboard template endpoints

Compliant with MCP specification for agent consumption.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.utils.dashboard_generator import DashboardGenerator

# Load environment
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="PE Dashboard MCP Server",
    description="Model Context Protocol server for Forbes AI 50 PE Dashboard",
    version="1.0.0"
)


# ============================================================================
# Pydantic Models
# ============================================================================

class CompanyIdList(BaseModel):
    """List of available company IDs"""
    company_ids: List[str] = Field(..., description="List of Forbes AI 50 company IDs")
    count: int = Field(..., description="Total number of companies")


class DashboardRequest(BaseModel):
    """Request model for dashboard generation"""
    company_id: str = Field(..., description="Company identifier (e.g., 'anthropic')")


class DashboardResponse(BaseModel):
    """Response model for dashboard generation"""
    company_id: str = Field(..., description="Company identifier")
    markdown: str = Field(..., description="Generated dashboard in Markdown format")
    method: str = Field(..., description="Generation method (structured or RAG)")
    generated_at: str = Field(..., description="Timestamp of generation")


class PromptResponse(BaseModel):
    """Response model for prompt templates"""
    id: str = Field(..., description="Prompt identifier")
    name: str = Field(..., description="Prompt name")
    description: str = Field(..., description="Prompt description")
    template: str = Field(..., description="8-section dashboard template")
    sections: List[str] = Field(..., description="List of dashboard sections")


class MCPInfo(BaseModel):
    """MCP server information"""
    name: str
    version: str
    description: str
    tools: List[str]
    resources: List[str]
    prompts: List[str]


# ============================================================================
# Helper Functions
# ============================================================================

def load_company_ids() -> List[str]:
    """Load company IDs from Forbes AI 50 seed data"""
    seed_paths = [
        Path("data/forbes_ai50_seed.json"),
        Path("../pe-dashboard-ai50/data/forbes_ai50_seed.json"),
        Path("../../pe-dashboard-ai50/data/forbes_ai50_seed.json")
    ]

    for path in seed_paths:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    companies = json.load(f)
                    return [c.get("company_id") for c in companies if c.get("company_id")]
            except Exception as e:
                print(f"Error loading {path}: {e}")

    # Fallback to payload directory
    payload_dirs = [
        Path("data/payloads"),
        Path("../pe-dashboard-ai50/data/payloads")
    ]

    for payload_dir in payload_dirs:
        if payload_dir.exists():
            payloads = list(payload_dir.glob("*_payload.json"))
            if payloads:
                return [p.stem.replace("_payload", "") for p in payloads]

    # Default fallback
    return ["anthropic", "openai", "cohere", "huggingface", "replicate"]


# ============================================================================
# MCP Server Info Endpoint
# ============================================================================

@app.get("/", response_model=MCPInfo)
async def get_mcp_info():
    """MCP server information and capabilities"""
    return MCPInfo(
        name="PE Dashboard MCP Server",
        version="1.0.0",
        description="Model Context Protocol server for Forbes AI 50 PE dashboards",
        tools=[
            "/tool/generate_structured_dashboard",
            "/tool/generate_rag_dashboard"
        ],
        resources=[
            "/resource/ai50/companies"
        ],
        prompts=[
            "/prompt/pe-dashboard"
        ]
    )


# ============================================================================
# RESOURCE Endpoints
# ============================================================================

@app.get("/resource/ai50/companies", response_model=CompanyIdList)
async def get_companies():
    """
    Resource: List all Forbes AI 50 company IDs

    Returns:
        CompanyIdList with available company identifiers
    """
    company_ids = load_company_ids()

    return CompanyIdList(
        company_ids=company_ids,
        count=len(company_ids)
    )


# ============================================================================
# TOOL Endpoints
# ============================================================================

@app.post("/tool/generate_structured_dashboard", response_model=DashboardResponse)
async def generate_structured_dashboard(request: DashboardRequest):
    """
    Tool: Generate structured dashboard from payload

    Uses pre-assembled company payloads from Assignment 2 to generate
    a comprehensive 8-section PE dashboard.

    Args:
        request: DashboardRequest with company_id

    Returns:
        DashboardResponse with Markdown dashboard
    """
    try:
        from datetime import datetime

        # Generate dashboard
        markdown = await DashboardGenerator.generate_structured_dashboard(request.company_id)

        return DashboardResponse(
            company_id=request.company_id,
            markdown=markdown,
            method="structured",
            generated_at=datetime.utcnow().isoformat()
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Payload not found for company '{request.company_id}': {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating structured dashboard: {str(e)}"
        )


@app.post("/tool/generate_rag_dashboard", response_model=DashboardResponse)
async def generate_rag_dashboard(request: DashboardRequest):
    """
    Tool: Generate RAG-based dashboard from vector DB

    Uses retrieval-augmented generation to synthesize dashboard content
    from company documents stored in Pinecone vector database.

    Args:
        request: DashboardRequest with company_id

    Returns:
        DashboardResponse with Markdown dashboard
    """
    try:
        from datetime import datetime

        # Generate dashboard
        markdown = await DashboardGenerator.generate_rag_dashboard(request.company_id)

        return DashboardResponse(
            company_id=request.company_id,
            markdown=markdown,
            method="RAG",
            generated_at=datetime.utcnow().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating RAG dashboard: {str(e)}"
        )


# ============================================================================
# PROMPT Endpoints
# ============================================================================

@app.get("/prompt/pe-dashboard", response_model=PromptResponse)
async def get_pe_dashboard_prompt():
    """
    Prompt: 8-section PE dashboard template

    Returns the standard template used for generating PE due diligence dashboards.

    Returns:
        PromptResponse with template and section list
    """
    sections = [
        "1. Company Overview",
        "2. Business Model and GTM",
        "3. Funding & Investor Profile",
        "4. Growth Momentum",
        "5. Visibility & Market Sentiment",
        "6. Risks and Challenges",
        "7. Outlook",
        "8. Disclosure Gaps"
    ]

    template = """# {company_name} - PE Due Diligence Dashboard

## 1. Company Overview
- Founded: {founded_year}
- Headquarters: {location}
- Website: {website}
- Description: {description}
- Leadership: {leadership}

## 2. Business Model and GTM
- Business Model: {business_model}
- Target Customers: {target_customers}
- Pricing: {pricing_model}
- Products/Services: {products}

## 3. Funding & Investor Profile
- Total Funding: {total_funding}
- Last Round: {last_round}
- Valuation: {valuation}
- Key Investors: {investors}

## 4. Growth Momentum
- Headcount: {headcount} (Growth: {growth_rate})
- Office Locations: {locations}
- Partnerships: {partnerships}
- Product Launches: {launches}

## 5. Visibility & Market Sentiment
- News Mentions: {news_mentions}
- Sentiment: {sentiment}
- Awards: {awards}

## 6. Risks and Challenges
{identified_risks}

## 7. Outlook
- Opportunities: {opportunities}
- Strategic Initiatives: {initiatives}

## 8. Disclosure Gaps
List of information not publicly disclosed:
{disclosure_gaps}

---
**Rules**:
- Use literal "Not disclosed." for missing fields
- Never invent ARR/MRR/valuation/customer counts
- Always include Disclosure Gaps section
"""

    return PromptResponse(
        id="pe-dashboard",
        name="PE Due Diligence Dashboard Template",
        description="8-section dashboard template for private equity due diligence on Forbes AI 50 companies",
        template=template,
        sections=sections
    )


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "server": "MCP PE Dashboard"}


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MCP_PORT", "9000"))
    host = os.getenv("MCP_HOST", "0.0.0.0")

    print(f"\n{'='*60}")
    print(f"🚀 MCP Server Starting")
    print(f"{'='*60}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"\nEndpoints:")
    print(f"  - Info:       http://{host}:{port}/")
    print(f"  - Resource:   http://{host}:{port}/resource/ai50/companies")
    print(f"  - Prompt:     http://{host}:{port}/prompt/pe-dashboard")
    print(f"  - Tool:       http://{host}:{port}/tool/generate_structured_dashboard")
    print(f"  - Tool:       http://{host}:{port}/tool/generate_rag_dashboard")
    print(f"  - Health:     http://{host}:{port}/health")
    print(f"{'='*60}\n")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )