import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from src.models import CompanyPayload


async def get_latest_structured_payload(company_id: str) -> Optional[CompanyPayload]:
    """
    Tool: get_latest_structured_payload

    Retrieve the latest fully assembled structured payload for a company.
    The payload includes:
      - company: Core company information
      - snapshot: Point-in-time metrics
      - investor_profile: Funding rounds and investors
      - growth_metrics: Headcount, partnerships, products
      - visibility: Market sentiment, news mentions
      - events: Timeline of company events
      - leadership: Leadership team members
      - products: Product portfolio

    Args:
        company_id: The canonical company_id (normalized, lowercase).

    Returns:
        A CompanyPayload object if found, None otherwise.

    Raises:
        FileNotFoundError: If payload file doesn't exist
        ValueError: If payload JSON is invalid
    """

    # Try multiple possible payload locations
    possible_paths = [
        # Assignment 2 structure (from original project)
        Path(f"../../pe-dashboard-ai50/data/payloads/{company_id}_payload.json"),
        Path(f"../pe-dashboard-ai50/data/payloads/{company_id}_payload.json"),
        Path(f"pe-dashboard-ai50/data/payloads/{company_id}_payload.json"),

        # v3 structure (if we create payloads here)
        Path(f"data/payloads/{company_id}_payload.json"),
        Path(f"../data/payloads/{company_id}_payload.json"),
    ]

    payload_path = None
    for path in possible_paths:
        if path.exists():
            payload_path = path
            break

    if not payload_path:
        raise FileNotFoundError(
            f"No payload found for company_id '{company_id}'. "
            f"Searched: {[str(p) for p in possible_paths]}"
        )

    # Load and parse JSON
    try:
        with open(payload_path, 'r', encoding='utf-8') as f:
            payload_data = json.load(f)

        # Validate and return as Pydantic model
        return CompanyPayload(**payload_data)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in payload file {payload_path}: {e}")
    except Exception as e:
        raise ValueError(f"Error loading payload for {company_id}: {e}")