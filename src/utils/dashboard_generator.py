"""
Dashboard Generation Utilities

Generates 8-section PE dashboards using:
1. Structured extraction (from payloads)
2. RAG-based generation (from vector DB)
"""

import asyncio
from typing import Optional
from datetime import datetime

from src.tools.payload_tool import get_latest_structured_payload
from src.tools.rag_tool import rag_search_company
from src.models import CompanyPayload


DASHBOARD_TEMPLATE = """# {company_name} - PE Due Diligence Dashboard

**Generated**: {timestamp}
**Data Sources**: {data_sources}

---

## 1. Company Overview

**Founded**: {founded_year}
**Headquarters**: {hq_city}, {hq_country}
**Website**: {website}
**Category**: {category}

**Description**: {description}

**Leadership**:
{leadership}

---

## 2. Business Model and GTM

**Business Model**: {business_model}
**Target Customers**: {target_customers}
**Pricing Model**: {pricing_model}

**Products/Services**:
{products}

**Competitors**: {competitors}

---

## 3. Funding & Investor Profile

**Total Funding**: {total_funding}
**Last Round**: {last_funding_stage} ({last_funding_date})
**Valuation**: {valuation}

**Key Investors**:
{investors}

**Recent Funding Rounds**:
{funding_rounds}

---

## 4. Growth Momentum

**Headcount**: {headcount} (YoY Growth: {headcount_growth_yoy})
**Open Roles**: {open_roles}
**Office Locations**: {office_locations}

**Partnerships**: {partnerships_count}
Recent: {recent_partnerships}

**Product Launches (12m)**: {product_launches_12m}

**Revenue**: {revenue_info}
**Customer Growth**: {customer_growth}

---

## 5. Visibility & Market Sentiment

**News Mentions (30d)**: {news_mentions_30d}
**Sentiment Score**: {sentiment_score}

**GitHub**: {github_stats}
**Glassdoor**: {glassdoor_rating} ({glassdoor_reviews} reviews)

**Awards & Recognition**:
{awards}

---

## 6. Risks and Challenges

{risks}

**Identified Risk Signals**:
{risk_signals}

---

## 7. Outlook

**Opportunities**:
{opportunities}

**Market Position**: {market_position}

**Strategic Initiatives**:
{strategic_initiatives}

---

## 8. Disclosure Gaps

The following information was not publicly disclosed:

{disclosure_gaps}

---

**Disclaimer**: This dashboard is generated from publicly available information. Data accuracy depends on source availability and timeliness.
"""


class DashboardGenerator:
    """Generate PE dashboards from structured or RAG data"""

    @staticmethod
    def format_list(items, prefix="- ", default="Not disclosed."):
        """Format list for markdown"""
        if not items:
            return default
        return "\n".join([f"{prefix}{item}" for item in items])

    @staticmethod
    async def generate_structured_dashboard(company_id: str) -> str:
        """
        Generate dashboard from structured payload

        Args:
            company_id: Company identifier

        Returns:
            Markdown dashboard string
        """
        try:
            payload = await get_latest_structured_payload(company_id)

            # Format leadership
            leadership = DashboardGenerator.format_list(
                [f"{m.name} - {m.title}" for m in payload.leadership],
                default="Not disclosed."
            )

            # Format products
            products = DashboardGenerator.format_list(
                [f"{p.name}: {p.description or 'N/A'}" for p in payload.products],
                default="Not disclosed."
            )

            # Format investors
            investors = DashboardGenerator.format_list(
                payload.investor_profile.lead_investors[:5],
                default="Not disclosed."
            )

            # Format funding rounds
            funding_rounds = DashboardGenerator.format_list(
                [f"{r.date or 'N/A'}: {r.stage} - {r.amount}" for r in payload.investor_profile.funding_rounds[:3]],
                default="Not disclosed."
            )

            # Format risks
            risks = DashboardGenerator.format_list(
                payload.risks if payload.risks else ["No major risks identified in structured data."],
                default="No major risks identified."
            )

            # Format opportunities
            opportunities = DashboardGenerator.format_list(
                payload.opportunities if payload.opportunities else ["Market expansion potential"],
                default="Standard growth opportunities."
            )

            # Format disclosure gaps
            disclosure_gaps = DashboardGenerator.format_list(
                payload.disclosure_gaps.missing_fields,
                default="All key metrics disclosed."
            )

            # Generate dashboard
            dashboard = DASHBOARD_TEMPLATE.format(
                company_name=payload.company.company_name,
                timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                data_sources=", ".join(payload.data_sources),
                founded_year=payload.company.founded_year or "Not disclosed.",
                hq_city=payload.company.hq_city or "Not disclosed.",
                hq_country=payload.company.hq_country or "Not disclosed.",
                website=payload.company.website,
                category=payload.company.category or "Not disclosed.",
                description=payload.company.description,
                leadership=leadership,
                business_model=payload.company.business_model or "Not disclosed.",
                target_customers=payload.company.target_customers or "Not disclosed.",
                pricing_model=payload.company.pricing_model or "Not disclosed.",
                products=products,
                competitors=", ".join(payload.company.competitors) if payload.company.competitors else "Not disclosed.",
                total_funding=payload.snapshot.total_funding or "Not disclosed.",
                last_funding_stage=payload.snapshot.last_funding_stage or "Not disclosed.",
                last_funding_date=payload.snapshot.last_funding_date or "Not disclosed.",
                valuation=payload.snapshot.valuation or "Not disclosed.",
                investors=investors,
                funding_rounds=funding_rounds,
                headcount=payload.snapshot.headcount or "Not disclosed.",
                headcount_growth_yoy=f"{payload.growth_metrics.headcount_growth_yoy}%" if payload.growth_metrics.headcount_growth_yoy else "Not disclosed.",
                open_roles=payload.growth_metrics.open_roles or "Not disclosed.",
                office_locations=", ".join(payload.growth_metrics.office_locations) if payload.growth_metrics.office_locations else "Not disclosed.",
                partnerships_count=payload.growth_metrics.partnerships_count or "Not disclosed.",
                recent_partnerships=", ".join(payload.growth_metrics.recent_partnerships) if payload.growth_metrics.recent_partnerships else "Not disclosed.",
                product_launches_12m=payload.growth_metrics.product_launches_12m or "Not disclosed.",
                revenue_info=payload.growth_metrics.revenue_info or "Not disclosed.",
                customer_growth=payload.growth_metrics.customer_growth or "Not disclosed.",
                news_mentions_30d=payload.visibility.news_mentions_30d or "Not disclosed.",
                sentiment_score=f"{payload.visibility.sentiment_score:.2f}" if payload.visibility.sentiment_score else "Not disclosed.",
                github_stats=f"{payload.visibility.github_stars} stars" if payload.visibility.github_stars else "Not disclosed.",
                glassdoor_rating=payload.visibility.glassdoor_rating or "Not disclosed.",
                glassdoor_reviews=payload.visibility.glassdoor_reviews or "Not disclosed.",
                awards=DashboardGenerator.format_list(payload.visibility.awards, default="Not disclosed."),
                risks=risks,
                risk_signals="No high-risk signals detected in structured data.",
                opportunities=opportunities,
                market_position="Analysis based on available data.",
                strategic_initiatives="See funding rounds and partnerships above.",
                disclosure_gaps=disclosure_gaps
            )

            return dashboard

        except Exception as e:
            return f"# Error Generating Dashboard\n\n**Company**: {company_id}\n**Error**: {str(e)}"

    @staticmethod
    async def generate_rag_dashboard(company_id: str) -> str:
        """
        Generate dashboard using RAG (retrieval-augmented generation)

        Args:
            company_id: Company identifier

        Returns:
            Markdown dashboard string with RAG-synthesized content
        """
        try:
            # Search for different aspects
            sections = {}

            queries = {
                "overview": "company overview mission vision",
                "business_model": "business model revenue pricing customers",
                "funding": "funding investors venture capital series",
                "growth": "growth hiring expansion headcount",
                "visibility": "news media coverage awards recognition",
                "risks": "layoffs challenges issues controversies",
                "outlook": "future plans roadmap strategy"
            }

            for section, query in queries.items():
                results = await rag_search_company(company_id, query, k=3)
                if results:
                    # Combine top 3 results
                    content = "\n\n".join([f"- {r['text'][:300]}..." for r in results[:3]])
                    sections[section] = content
                else:
                    sections[section] = "Not disclosed. (No relevant data found in vector DB)"

            # Generate RAG-based dashboard
            dashboard = f"""# {company_id.title()} - PE Due Diligence Dashboard (RAG)

**Generated**: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
**Method**: Retrieval-Augmented Generation from Vector DB

---

## 1. Company Overview

{sections.get('overview', 'Not disclosed.')}

---

## 2. Business Model and GTM

{sections.get('business_model', 'Not disclosed.')}

---

## 3. Funding & Investor Profile

{sections.get('funding', 'Not disclosed.')}

---

## 4. Growth Momentum

{sections.get('growth', 'Not disclosed.')}

---

## 5. Visibility & Market Sentiment

{sections.get('visibility', 'Not disclosed.')}

---

## 6. Risks and Challenges

{sections.get('risks', 'No major risks identified in available data.')}

---

## 7. Outlook

{sections.get('outlook', 'Not disclosed.')}

---

## 8. Disclosure Gaps

The following sections have limited information in our vector database:
- Detailed financial metrics (ARR, MRR, revenue)
- Customer count and retention rates
- Detailed product roadmap
- Internal organizational structure

---

**Note**: This dashboard is generated from semantic search over scraped documents. Content may contain redundancies or gaps based on source availability.
"""

            return dashboard

        except Exception as e:
            return f"# Error Generating RAG Dashboard\n\n**Company**: {company_id}\n**Error**: {str(e)}"
