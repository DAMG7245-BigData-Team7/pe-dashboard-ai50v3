"""
ReAct Pattern Logger

Logs Thought → Action → Observation triplets in structured JSON format.
Supports correlation IDs (run_id, company_id) for tracing workflow execution.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ReActLogger:
    """Structured logger for ReAct (Reasoning + Acting) agent traces"""

    def __init__(self, log_file: str = "logs/react_traces.jsonl", run_id: Optional[str] = None):
        """
        Initialize ReAct logger

        Args:
            log_file: Path to JSONL log file
            run_id: Unique run identifier (generated if not provided)
        """
        self.log_file = Path(log_file)
        self.run_id = run_id or str(uuid4())
        self.step_counter = 0

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"ReAct Logger initialized | run_id={self.run_id}")

    def log_thought(self, thought: str, company_id: Optional[str] = None, metadata: Optional[Dict] = None):
        """Log agent's reasoning/thought"""
        self._log_step(
            step_type="thought",
            content=thought,
            company_id=company_id,
            metadata=metadata
        )

    def log_action(self, tool_name: str, tool_input: Dict, company_id: Optional[str] = None, metadata: Optional[Dict] = None):
        """Log agent's action (tool invocation)"""
        self._log_step(
            step_type="action",
            content={
                "tool": tool_name,
                "input": tool_input
            },
            company_id=company_id,
            metadata=metadata
        )

    def log_observation(self, observation: Any, company_id: Optional[str] = None, metadata: Optional[Dict] = None):
        """Log observation from tool execution"""
        # Truncate large observations
        obs_str = str(observation)
        if len(obs_str) > 500:
            obs_str = obs_str[:500] + "... (truncated)"

        self._log_step(
            step_type="observation",
            content=obs_str,
            company_id=company_id,
            metadata=metadata
        )

    def log_final_answer(self, answer: str, company_id: Optional[str] = None, metadata: Optional[Dict] = None):
        """Log agent's final answer"""
        self._log_step(
            step_type="final_answer",
            content=answer,
            company_id=company_id,
            metadata=metadata
        )

    def _log_step(
        self,
        step_type: str,
        content: Any,
        company_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Internal method to log a ReAct step"""
        self.step_counter += 1

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": self.run_id,
            "step": self.step_counter,
            "type": step_type,
            "content": content,
            "company_id": company_id,
            "metadata": metadata or {}
        }

        # Write to JSONL file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write ReAct log: {e}")

        # Console output for visibility
        emoji = {
            "thought": "💭",
            "action": "🔧",
            "observation": "👁️",
            "final_answer": "✅"
        }.get(step_type, "📝")

        print(f"\n{emoji} [{step_type.upper()}] Step {self.step_counter}")
        if isinstance(content, dict):
            print(json.dumps(content, indent=2))
        else:
            print(content)

    def get_trace_summary(self) -> Dict:
        """Get summary of current trace"""
        return {
            "run_id": self.run_id,
            "total_steps": self.step_counter,
            "log_file": str(self.log_file)
        }
