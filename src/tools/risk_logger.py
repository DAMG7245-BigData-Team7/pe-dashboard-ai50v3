import json
import logging
from datetime import date, datetime
from pathlib import Path
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)


class LayoffSignal(BaseModel):
    """Structured description of a potential layoff / risk signal."""
    company_id: str = Field(..., description="Company identifier")
    occurred_on: date = Field(..., description="Date when the event occurred")
    description: str = Field(..., description="Description of the risk signal")
    source_url: HttpUrl = Field(..., description="Source URL for the information")
    severity: Optional[str] = Field("medium", description="Risk severity: low, medium, high")
    detected_at: Optional[str] = Field(None, description="Timestamp when signal was detected")

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v)
        }


async def report_layoff_signal(
    signal_data: LayoffSignal,
    log_file: str = "data/risk_signals.jsonl"
) -> bool:
    """
    Tool: report_layoff_signal

    Record a high-risk layoff / workforce reduction / negative event for the given company.

    This tool writes to a structured JSONL (JSON Lines) file for persistence and analysis.
    Each signal is logged with timestamp, company info, and source provenance.

    Args:
        signal_data: LayoffSignal with company_id, occurred_on, description, and source_url.
        log_file: Path to JSONL log file (default: "data/risk_signals.jsonl").

    Returns:
        True if logging succeeded, False otherwise.

    Side Effects:
        - Creates data/ directory if it doesn't exist
        - Appends signal to JSONL file
        - Logs to console for immediate visibility
    """

    try:
        # Ensure data directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Add detection timestamp if not present
        if not signal_data.detected_at:
            signal_data.detected_at = datetime.utcnow().isoformat()

        # Convert to dict for JSON serialization
        signal_dict = {
            "company_id": signal_data.company_id,
            "occurred_on": signal_data.occurred_on.isoformat(),
            "description": signal_data.description,
            "source_url": str(signal_data.source_url),
            "severity": signal_data.severity,
            "detected_at": signal_data.detected_at
        }

        # Append to JSONL file (one JSON object per line)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(signal_dict) + '\n')

        # Console logging for immediate visibility
        logger.warning(
            f"🚨 RISK SIGNAL DETECTED | {signal_data.company_id} | "
            f"{signal_data.severity.upper()} | {signal_data.description} | "
            f"Source: {signal_data.source_url}"
        )

        print(
            f"\n🚨 RISK SIGNAL LOGGED\n"
            f"  Company: {signal_data.company_id}\n"
            f"  Date: {signal_data.occurred_on}\n"
            f"  Severity: {signal_data.severity}\n"
            f"  Description: {signal_data.description}\n"
            f"  Source: {signal_data.source_url}\n"
            f"  Logged to: {log_path}\n"
        )

        return True

    except Exception as e:
        logger.error(f"Failed to log risk signal for {signal_data.company_id}: {e}")
        print(f"❌ Error logging risk signal: {e}")
        return False