"""
Dashboard Generation Utilities with LLM Synthesis

Generates 8-section PE dashboards using:
1. Structured extraction (from payloads) → LLM synthesis
2. RAG-based generation (from vector DB) → LLM synthesis

UPDATED: Now includes OpenAI LLM calls for professional narrative generation
"""

import os
import asyncio
import json
from typing import Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from src.tools.payload_tool import get_latest_structured_payload
from src.tools.rag_tool import rag_search_company
from src.models import CompanyPayload

# Load environment
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================================
# System Prompts & Templates
# ============================================================================

PE_ANALYST_SYSTEM_PROMPT = """You are an expert private equity analyst generating due diligence dashboards for institutional investors.

CRITICAL REQUIREMENTS:

1. **Structure**: Generate EXACTLY 8 sections in this order:
   - 1. Company Overview
   - 2. Business Model and GTM
   - 3. Funding & Investor Profile
   - 4. Growth Momentum
   - 5. Visibility & Market Sentiment
   - 6. Risks and Challenges
   - 7. Outlook
   - 8. Disclosure Gaps

2. **Accuracy**: 
   - Use ONLY information provided in the context
   - For missing information, write "Not disclosed."
   - NEVER invent metrics, valuations, or customer counts
   - Include specific numbers and dates when available

3. **Style**:
   - Professional, analytical tone
   - Clear, concise narratives (not bullet points unless listing items)
   - Synthesize information, don't just copy-paste
   - Focus on investor-relevant insights

4. **Disclosure Gaps**:
   - Always end with Section 8
   - List specific metrics/information not publicly available
   - Be honest about data limitations

Generate a comprehensive, investor-grade dashboard that helps LPs make informed decisions."""


DASHBOARD_GENERATION_PROMPT = """Generate a comprehensive PE due diligence dashboard for **{company_name}**.

Create an 8-section markdown dashboard following this structure:

# {company_name} - PE Due Diligence Dashboard

**Generated**: {timestamp}

---

## 1. Company Overview
Provide: Founding year, headquarters location, category/vertical, mission, key leadership (if available). Synthesize into 2-3 paragraphs.

## 2. Business Model and GTM
Analyze: Business model (B2B/B2C/etc), target customers, pricing strategy, products/services, go-to-market approach, competitive positioning.

## 3. Funding & Investor Profile
Summarize: Total funding raised, funding rounds with dates and amounts, lead investors, current valuation, investor composition.

## 4. Growth Momentum
Assess: Headcount trends, hiring activity, office locations/expansion, partnerships, product launches, customer/revenue growth signals.

## 5. Visibility & Market Sentiment
Evaluate: News mentions, media coverage, awards/recognition, GitHub activity (if applicable), Glassdoor ratings, public perception.

## 6. Risks and Challenges
Identify: Competitive threats, operational challenges, regulatory concerns, market risks, recent controversies or negative signals.

## 7. Outlook
Discuss: Growth opportunities, strategic initiatives, market positioning, future prospects based on available data.

## 8. Disclosure Gaps
List: Specific information NOT publicly disclosed (e.g., "Revenue details", "Customer count", "Detailed valuation").

---

**CONTEXT PROVIDED BELOW:**
"""


# ============================================================================
# Dashboard Generator Class
# ============================================================================

class DashboardGenerator:
    """Generate PE dashboards with LLM synthesis"""

    @staticmethod
    def format_list(items, prefix="- ", default="Not disclosed."):
        """Format list for markdown"""
        if not items:
            return default
        return "\n".join([f"{prefix}{item}" for item in items])

    @staticmethod
    async def generate_structured_dashboard(company_id: str, model: str = "gpt-4o-mini") -> str:
        """
        Generate dashboard from structured payload using LLM synthesis

        Args:
            company_id: Company identifier
            model: OpenAI model to use

        Returns:
            Markdown dashboard string
        """
        try:
            # Step 1: Load structured payload
            payload = await get_latest_structured_payload(company_id)

        except FileNotFoundError as e:
            # Return informative message when payload doesn't exist
            return f"""# {company_id.title()} - PE Due Diligence Dashboard (Structured)

**Generated**: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
**Status**: ⚠️ Payload Not Available

---

## Data Availability Notice

The structured payload file for **{company_id}** is not available in this deployment.

**Note:** This company's data has not been processed through the structured extraction pipeline.
Please ensure the company has been scraped and extracted before generating dashboards.

---

**Alternative:** Use the RAG-based dashboard which retrieves data from the vector database.
"""

        try:
            # Step 2: Format payload data as rich context for LLM
            
            # Helper functions
            def fmt_funding_rounds(rounds):
                if not rounds:
                    return "No funding rounds disclosed"
                lines = []
                for r in rounds[:5]:
                    date = r.date or "Date unknown"
                    stage = r.stage or "Unknown stage"
                    amount = r.amount or "Not disclosed"
                    lead = r.lead_investor or "Not disclosed"
                    valuation = r.valuation or "Not disclosed"
                    lines.append(f"- {date}: {stage}, Amount: {amount}, Lead: {lead}, Valuation: {valuation}")
                return "\n".join(lines)
            
            def fmt_events(events):
                if not events:
                    return "No major events disclosed"
                lines = []
                for e in events[:8]:
                    date = e.date or "Date unknown"
                    title = e.title
                    etype = e.event_type
                    lines.append(f"- {date} ({etype}): {title}")
                return "\n".join(lines)
            
            # Build comprehensive context
            context = f"""
## COMPANY INFORMATION

**Basic Info:**
- Company Name: {payload.company.company_name}
- Company ID: {payload.company.company_id}
- Website: {payload.company.website}
- LinkedIn: {payload.company.linkedin or "Not disclosed"}
- Founded: {payload.company.founded_year or "Not disclosed"}
- Headquarters: {payload.company.hq_city or "Not disclosed"}, {payload.company.hq_country or "Not disclosed"}
- Category: {payload.company.category or "Not disclosed"}
- Subcategory: {payload.company.subcategory or "Not disclosed"}

**Description:**
{payload.company.description}

**Tagline:**
{payload.company.tagline or "Not disclosed"}

**Leadership Team:**
{DashboardGenerator.format_list([f"{m.name} - {m.title}" for m in payload.leadership], default="Leadership information not disclosed")}

**Business Model:**
- Type: {payload.company.business_model or "Not disclosed"}
- Target Customers: {payload.company.target_customers or "Not disclosed"}
- Pricing Model: {payload.company.pricing_model or "Not disclosed"}

**Products/Services:**
{DashboardGenerator.format_list([f"{p.name}: {p.description or 'Description not available'}" for p in payload.products], default="Product information not disclosed")}

**Known Competitors:**
{", ".join(payload.company.competitors) if payload.company.competitors else "Not disclosed"}

---

## SNAPSHOT (as of {payload.snapshot.snapshot_date})

**Funding:**
- Total Funding: {payload.snapshot.total_funding or "Not disclosed"}
- Total Funding (Numeric): {f"${payload.snapshot.total_funding_numeric}M" if payload.snapshot.total_funding_numeric else "Not disclosed"}
- Last Funding Date: {payload.snapshot.last_funding_date or "Not disclosed"}
- Last Funding Stage: {payload.snapshot.last_funding_stage or "Not disclosed"}
- Current Valuation: {payload.snapshot.valuation or "Not disclosed"}

**Team:**
- Headcount: {payload.snapshot.headcount or "Not disclosed"}
- Leadership Count: {payload.snapshot.leadership_count or "Not disclosed"}

**Traction:**
- Customer Count: {payload.snapshot.customer_count or "Not disclosed"}
- Revenue Range: {payload.snapshot.revenue_range or "Not disclosed"}

---

## FUNDING HISTORY

**Total Raised:** {payload.investor_profile.total_raised or "Not disclosed"}
**Number of Rounds:** {len(payload.investor_profile.funding_rounds)}

**Funding Rounds:**
{fmt_funding_rounds(payload.investor_profile.funding_rounds)}

**Lead Investors:**
{", ".join(payload.investor_profile.lead_investors[:10]) if payload.investor_profile.lead_investors else "Not disclosed"}

**All Investors ({len(payload.investor_profile.all_investors)} total):**
{", ".join(payload.investor_profile.all_investors[:15]) if payload.investor_profile.all_investors else "Not disclosed"}

**Last Round Date:** {payload.investor_profile.last_round_date or "Not disclosed"}

---

## GROWTH METRICS

**Headcount & Hiring:**
- Current Headcount: {payload.growth_metrics.headcount or "Not disclosed"}
- YoY Growth: {f"{payload.growth_metrics.headcount_growth_yoy}%" if payload.growth_metrics.headcount_growth_yoy else "Not disclosed"}
- Open Roles: {payload.growth_metrics.open_roles or "Not disclosed"}
- Recent Hires (6m): {payload.growth_metrics.recent_hires or "Not disclosed"}

**Geographic Presence:**
- Office Locations: {", ".join(payload.growth_metrics.office_locations) if payload.growth_metrics.office_locations else "Not disclosed"}
- Geographic Expansion: {payload.growth_metrics.geographic_expansion or "Not disclosed"}

**Partnerships:**
- Total Partnerships: {payload.growth_metrics.partnerships_count or "Not disclosed"}
- Recent Partnerships: {", ".join(payload.growth_metrics.recent_partnerships) if payload.growth_metrics.recent_partnerships else "Not disclosed"}

**Product Momentum:**
- Product Launches (12m): {payload.growth_metrics.product_launches_12m or "Not disclosed"}
- Recent Products: {", ".join(payload.growth_metrics.recent_products) if payload.growth_metrics.recent_products else "Not disclosed"}

**Revenue & Customers:**
- Revenue Info: {payload.growth_metrics.revenue_info or "Not disclosed"}
- Customer Growth: {payload.growth_metrics.customer_growth or "Not disclosed"}

**Market Presence:**
- Press Mentions (12m): {payload.growth_metrics.press_mentions_12m or "Not disclosed"}
- Website Traffic Trend: {payload.growth_metrics.website_traffic_trend or "Not disclosed"}

---

## VISIBILITY & MARKET SENTIMENT

- News Mentions (30d): {payload.visibility.news_mentions_30d or "Not disclosed"}
- Sentiment Score: {f"{payload.visibility.sentiment_score:.2f}" if payload.visibility.sentiment_score else "Not disclosed"}
- GitHub Stars: {payload.visibility.github_stars or "Not disclosed"}
- GitHub URL: {payload.visibility.github_url or "Not disclosed"}
- Glassdoor Rating: {payload.visibility.glassdoor_rating or "Not disclosed"}
- Glassdoor Reviews: {payload.visibility.glassdoor_reviews or "Not disclosed"}

**Awards & Recognition:**
{DashboardGenerator.format_list(payload.visibility.awards, default="No awards information available")}

**Notable Media Coverage:**
{DashboardGenerator.format_list(payload.visibility.media_coverage, default="No media coverage tracked")}

---

## COMPANY TIMELINE

**Major Events:**
{fmt_events(payload.events)}

---

## RISK ASSESSMENT

**Identified Risks:**
{DashboardGenerator.format_list(payload.risks, default="No major risks identified in available data")}

**Opportunities:**
{DashboardGenerator.format_list(payload.opportunities, default="Standard market opportunities")}

**Analyst Notes:**
{payload.analyst_notes or "No additional analyst notes"}

---

## DATA SOURCES

{", ".join(payload.data_sources)}

**Extracted At:** {payload.extracted_at}

---

## DISCLOSURE GAPS

The following information was not publicly disclosed:
{DashboardGenerator.format_list(payload.disclosure_gaps.missing_fields, default="All key information disclosed")}

**Confidence Notes:**
{json.dumps(payload.disclosure_gaps.confidence_notes, indent=2) if payload.disclosure_gaps.confidence_notes else "No confidence notes"}
"""

            # Step 3: Generate dashboard using LLM
            prompt = DASHBOARD_GENERATION_PROMPT.format(
                company_name=payload.company.company_name,
                timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            )

            full_prompt = f"{prompt}\n\n{context}\n\nGenerate the complete 8-section dashboard now."

            # Call OpenAI
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": PE_ANALYST_SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.3,  # Slightly creative but mostly factual
                max_tokens=3000
            )

            dashboard = response.choices[0].message.content

            return dashboard

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"# Error Generating Dashboard\n\n**Company**: {company_id}\n**Error**: {str(e)}"

    @staticmethod
    async def generate_rag_dashboard(company_id: str, model: str = "gpt-4o-mini") -> str:
        """
        Generate dashboard using RAG (retrieval-augmented generation) with LLM synthesis

        Args:
            company_id: Company identifier
            model: OpenAI model to use

        Returns:
            Markdown dashboard string with LLM-synthesized content
        """
        try:
            # Step 1: Retrieve relevant chunks from vector DB for each section
            print(f"🔍 Retrieving information for {company_id} from Pinecone...")

            queries = {
                "overview": "company overview founding mission vision description headquarters",
                "business_model": "business model revenue pricing customers products services GTM strategy",
                "funding": "funding rounds investors venture capital series A B C valuation",
                "growth": "growth hiring headcount expansion employees partnerships",
                "visibility": "news media coverage press mentions awards recognition",
                "risks": "layoffs challenges issues controversies problems concerns",
                "outlook": "future plans roadmap strategy opportunities initiatives"
            }

            all_chunks = []
            section_contexts = {}

            for section, query in queries.items():
                results = await rag_search_company(company_id, query, k=5)
                
                if results:
                    # Combine chunks with source attribution
                    section_text = []
                    for r in results:
                        page_type = r['metadata'].get('page_type', 'unknown')
                        text = r['text']
                        section_text.append(f"[Source: {page_type}] {text}")
                    
                    section_contexts[section] = "\n\n".join(section_text)
                    all_chunks.extend(results)
                else:
                    section_contexts[section] = f"No information found in vector database for {section}."

            if not all_chunks:
                return f"""# {company_id.title()} - PE Due Diligence Dashboard (RAG)

**Generated**: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
**Status**: ⚠️ No Data Available

---

## Data Availability Notice

No information was found in the vector database for **{company_id}**.

This may be because:
1. The company has not been scraped yet
2. The vector database has not been built
3. The company_id may be incorrect

Please ensure the company data exists in Pinecone before generating RAG dashboards.
"""

            print(f"✅ Retrieved {len(all_chunks)} total chunks from vector DB")

            # Step 2: Build comprehensive context
            context = f"""
## RETRIEVED INFORMATION FOR {company_id.upper()}

### Company Overview & Description
{section_contexts.get('overview', 'Not disclosed.')}

### Business Model, Products & GTM
{section_contexts.get('business_model', 'Not disclosed.')}

### Funding, Investors & Valuation
{section_contexts.get('funding', 'Not disclosed.')}

### Growth, Hiring & Expansion
{section_contexts.get('growth', 'Not disclosed.')}

### Visibility, News & Market Sentiment
{section_contexts.get('visibility', 'Not disclosed.')}

### Risks, Challenges & Issues
{section_contexts.get('risks', 'No major risks identified in available data.')}

### Future Plans, Strategy & Outlook
{section_contexts.get('outlook', 'Not disclosed.')}

---

**Total Chunks Retrieved:** {len(all_chunks)}
**Unique Sources:** {len(set(c['metadata'].get('page_type') for c in all_chunks if c.get('metadata')))}
"""

            # Step 3: Generate dashboard using LLM
            prompt = DASHBOARD_GENERATION_PROMPT.format(
                company_name=company_id.title(),
                timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            )

            full_prompt = f"{prompt}\n\n{context}\n\nSynthesize the above information into a professional 8-section PE dashboard."

            print(f"🤖 Calling OpenAI {model} to synthesize dashboard...")

            # Call OpenAI
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": PE_ANALYST_SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )

            dashboard = response.choices[0].message.content

            print(f"✅ Generated RAG dashboard ({len(dashboard)} chars)")

            return dashboard

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"# Error Generating RAG Dashboard\n\n**Company**: {company_id}\n**Error**: {str(e)}"

    @staticmethod
    def save_dashboard(company_id: str, dashboard_content: str, method: str, run_id: str = None) -> Path:
        """
        Save generated dashboard to disk

        Args:
            company_id: Company identifier
            dashboard_content: Dashboard markdown content
            method: Generation method ('structured' or 'rag')
            run_id: Optional workflow run ID for tracking

        Returns:
            Path to saved dashboard file
        """
        # Create dashboards directory
        dashboards_dir = Path("data/dashboards")
        dashboards_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if run_id:
            filename = f"{company_id}_{method}_{timestamp}_{run_id[:8]}.md"
        else:
            filename = f"{company_id}_{method}_{timestamp}.md"

        filepath = dashboards_dir / filename

        # Write dashboard to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(dashboard_content)

        print(f"💾 Dashboard saved: {filepath}")

        return filepath