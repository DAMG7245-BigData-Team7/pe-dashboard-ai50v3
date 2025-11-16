"""
Unit tests for core agent tools (Lab 12 Checkpoint)

Tests the three core tools:
1. get_latest_structured_payload - Load company payloads
2. rag_search_company - Query vector DB
3. report_layoff_signal - Log risk signals
"""

import pytest
import json
import os
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from src.tools.payload_tool import get_latest_structured_payload
from src.tools.rag_tool import rag_search_company
from src.tools.risk_logger import report_layoff_signal, LayoffSignal
from src.models import CompanyPayload


# ============================================================
# Test 1: get_latest_structured_payload
# ============================================================

@pytest.mark.asyncio
async def test_get_latest_structured_payload_success():
    """Test successful payload loading"""

    # Mock payload data (minimal valid CompanyPayload)
    mock_payload_data = {
        "company": {
            "company_name": "Anthropic",
            "company_id": "anthropic",
            "website": "https://www.anthropic.com",
            "description": "AI safety company"
        },
        "snapshot": {
            "snapshot_date": "2025-01-01",
            "total_funding": "$7.6B",
            "headcount": 500
        },
        "investor_profile": {
            "total_raised": "$7.6B",
            "funding_rounds": []
        },
        "growth_metrics": {
            "headcount": 500,
            "office_locations": ["San Francisco"]
        },
        "visibility": {
            "news_mentions_30d": 100
        },
        "events": [],
        "funding_rounds": [],
        "leadership": [],
        "products": [],
        "disclosure_gaps": {"missing_fields": []},
        "data_sources": ["forbes"],
        "extracted_at": "2025-01-01T00:00:00"
    }

    mock_json_content = json.dumps(mock_payload_data)

    # Mock file operations
    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=mock_json_content)):
            result = await get_latest_structured_payload("anthropic")

    # Assertions
    assert result is not None
    assert isinstance(result, CompanyPayload)
    assert result.company.company_id == "anthropic"
    assert result.company.company_name == "Anthropic"


@pytest.mark.asyncio
async def test_get_latest_structured_payload_not_found():
    """Test handling when payload file doesn't exist"""

    with patch('pathlib.Path.exists', return_value=False):
        with pytest.raises(FileNotFoundError) as exc_info:
            await get_latest_structured_payload("nonexistent_company")

        assert "No payload found" in str(exc_info.value)
        assert "nonexistent_company" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_latest_structured_payload_invalid_json():
    """Test handling of invalid JSON in payload file"""

    invalid_json = "{ this is not valid json }"

    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=invalid_json)):
            with pytest.raises(ValueError) as exc_info:
                await get_latest_structured_payload("test_company")

            assert "Invalid JSON" in str(exc_info.value)


# ============================================================
# Test 2: rag_search_company
# ============================================================

@pytest.mark.asyncio
async def test_rag_search_company_success():
    """Test successful RAG search with mocked Pinecone"""

    # Mock environment variables
    with patch.dict(os.environ, {
        'PINECONE_API_KEY': 'test-pinecone-key',
        'OPENAI_API_KEY': 'test-openai-key'
    }):
        # Mock OpenAI embedding response
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]

        # Mock Pinecone query results
        mock_pinecone_results = {
            'matches': [
                {
                    'id': 'anthropic_1',
                    'score': 0.92,
                    'metadata': {
                        'company_id': 'anthropic',
                        'page_type': 'blog',
                        'text': 'Anthropic recently raised $7.6B in funding.',
                        'token_count': 10
                    }
                },
                {
                    'id': 'anthropic_2',
                    'score': 0.85,
                    'metadata': {
                        'company_id': 'anthropic',
                        'page_type': 'homepage',
                        'text': 'We are hiring 100 new engineers.',
                        'token_count': 8
                    }
                }
            ]
        }

        # Mock Pinecone and OpenAI clients
        with patch('src.tools.rag_tool.Pinecone') as mock_pinecone_class:
            with patch('src.tools.rag_tool.OpenAI') as mock_openai_class:
                # Setup mocks
                mock_index = MagicMock()
                mock_index.query.return_value = mock_pinecone_results
                mock_pinecone_class.return_value.Index.return_value = mock_index

                mock_openai_client = MagicMock()
                mock_openai_client.embeddings.create.return_value = mock_embedding_response
                mock_openai_class.return_value = mock_openai_client

                # Execute test
                results = await rag_search_company("anthropic", "funding rounds", k=2)

        # Assertions
        assert len(results) == 2
        assert results[0]['text'] == 'Anthropic recently raised $7.6B in funding.'
        assert results[0]['score'] == 0.92
        assert results[0]['metadata']['company_id'] == 'anthropic'
        assert results[0]['metadata']['page_type'] == 'blog'


@pytest.mark.asyncio
async def test_rag_search_company_missing_api_keys():
    """Test error handling when API keys are missing"""

    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            await rag_search_company("anthropic", "test query")

        assert "PINECONE_API_KEY" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rag_search_company_empty_results():
    """Test handling when no results are returned"""

    with patch.dict(os.environ, {
        'PINECONE_API_KEY': 'test-key',
        'OPENAI_API_KEY': 'test-key'
    }):
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]

        mock_pinecone_results = {'matches': []}  # Empty results

        with patch('src.tools.rag_tool.Pinecone') as mock_pinecone_class:
            with patch('src.tools.rag_tool.OpenAI') as mock_openai_class:
                mock_index = MagicMock()
                mock_index.query.return_value = mock_pinecone_results
                mock_pinecone_class.return_value.Index.return_value = mock_index

                mock_openai_client = MagicMock()
                mock_openai_client.embeddings.create.return_value = mock_embedding_response
                mock_openai_class.return_value = mock_openai_client

                results = await rag_search_company("test_company", "query", k=5)

        assert len(results) == 0


# ============================================================
# Test 3: report_layoff_signal
# ============================================================

@pytest.mark.asyncio
async def test_report_layoff_signal_success(tmp_path):
    """Test successful risk signal logging"""

    # Create temporary log file path
    log_file = tmp_path / "test_risk_signals.jsonl"

    # Create test signal
    signal = LayoffSignal(
        company_id="test_company",
        occurred_on=date(2025, 1, 15),
        description="Company announced 20% workforce reduction",
        source_url="https://techcrunch.com/test-layoffs",
        severity="high"
    )

    # Execute test
    result = await report_layoff_signal(signal, log_file=str(log_file))

    # Assertions
    assert result is True
    assert log_file.exists()

    # Verify JSONL content
    with open(log_file, 'r') as f:
        logged_data = json.loads(f.readline())

    assert logged_data['company_id'] == "test_company"
    assert logged_data['occurred_on'] == "2025-01-15"
    assert logged_data['description'] == "Company announced 20% workforce reduction"
    assert logged_data['severity'] == "high"
    assert 'detected_at' in logged_data


@pytest.mark.asyncio
async def test_report_layoff_signal_multiple_signals(tmp_path):
    """Test logging multiple signals to same file"""

    log_file = tmp_path / "multi_signals.jsonl"

    signals = [
        LayoffSignal(
            company_id="company_a",
            occurred_on=date(2025, 1, 10),
            description="First layoff event",
            source_url="https://example.com/1"
        ),
        LayoffSignal(
            company_id="company_b",
            occurred_on=date(2025, 1, 12),
            description="Second layoff event",
            source_url="https://example.com/2"
        )
    ]

    # Log both signals
    for signal in signals:
        result = await report_layoff_signal(signal, log_file=str(log_file))
        assert result is True

    # Verify both signals are in file
    with open(log_file, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 2
    assert json.loads(lines[0])['company_id'] == "company_a"
    assert json.loads(lines[1])['company_id'] == "company_b"


@pytest.mark.asyncio
async def test_report_layoff_signal_creates_directory(tmp_path):
    """Test that report_layoff_signal creates parent directories"""

    # Use nested path that doesn't exist
    log_file = tmp_path / "nested" / "directory" / "signals.jsonl"

    signal = LayoffSignal(
        company_id="test",
        occurred_on=date(2025, 1, 1),
        description="Test signal",
        source_url="https://example.com/test"
    )

    result = await report_layoff_signal(signal, log_file=str(log_file))

    assert result is True
    assert log_file.exists()
    assert log_file.parent.exists()


# ============================================================
# Integration Test (Optional)
# ============================================================

@pytest.mark.asyncio
async def test_tools_integration():
    """
    High-level integration test simulating agent workflow:
    1. Load payload
    2. Search RAG
    3. Detect risk and log signal
    """

    # This is a simplified integration test
    # In real scenario, you'd have actual data and Pinecone index

    # For now, just verify all three tools can be imported and called
    from src.tools.payload_tool import get_latest_structured_payload
    from src.tools.rag_tool import rag_search_company
    from src.tools.risk_logger import report_layoff_signal, LayoffSignal

    # Verify functions are callable
    assert callable(get_latest_structured_payload)
    assert callable(rag_search_company)
    assert callable(report_layoff_signal)

    # Verify models can be instantiated
    signal = LayoffSignal(
        company_id="test",
        occurred_on=date.today(),
        description="Test",
        source_url="https://example.com"
    )
    assert signal.company_id == "test"