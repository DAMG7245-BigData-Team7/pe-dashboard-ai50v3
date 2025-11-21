import os
from typing import List, Dict
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class RAGChunk(BaseModel):
    """Retrieved chunk from vector database"""
    text: str = Field(..., description="Retrieved text passage")
    source_url: str = Field(..., description="Source URL or reference")
    score: float = Field(..., description="Relevance score (0-1)")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


async def rag_search_company(
    company_id: str,
    query: str,
    k: int = 5,
    index_name: str = "pe-dashboard-ai50",
    embedding_model: str = "text-embedding-3-small"
) -> List[Dict]:
    """
    Tool: rag_search_company

    Perform retrieval-augmented search for the specified company and query.
    Searches Pinecone vector DB created in Assignment 2.

    Args:
        company_id: The canonical company identifier (normalized, lowercase).
        query: Natural language query string (e.g., "layoffs OR workforce reduction").
        k: Number of top results to return (default: 5).
        index_name: Pinecone index name (default: "pe-dashboard-ai50").
        embedding_model: OpenAI embedding model (default: "text-embedding-3-small").

    Returns:
        A list of chunks with metadata:
        [
          {"text": "<retrieved passage>",
           "source_url": "https://company.com/...",
           "score": 0.87,
           "metadata": {"page_type": "blog", "company_id": "anthropic"}},
          ...
        ]

    Raises:
        ValueError: If API keys are missing or index doesn't exist
    """

    # Get API keys from environment
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY not found in environment variables")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Initialize clients
    try:
        pc = Pinecone(api_key=pinecone_api_key)
        openai_client = OpenAI(api_key=openai_api_key)
        index = pc.Index(index_name)

    except Exception as e:
        raise ValueError(f"Failed to connect to Pinecone index '{index_name}': {e}")

    # Generate query embedding
    try:
        response = openai_client.embeddings.create(
            model=embedding_model,
            input=query
        )
        query_vector = response.data[0].embedding

    except Exception as e:
        raise ValueError(f"Failed to generate embedding for query: {e}")

    # Search Pinecone with company filter
    try:
        results = index.query(
            vector=query_vector,
            top_k=k,
            include_metadata=True,
            filter={'company_id': company_id}  # Filter to specific company
        )

    except Exception as e:
        raise ValueError(f"Pinecone query failed: {e}")

    # Format results
    formatted_results = []
    for match in results.get('matches', []):
        metadata = match.get('metadata', {})

        formatted_results.append({
            'text': metadata.get('text', ''),
            'source_url': metadata.get('source_file', f"https://{company_id}.com"),  # Fallback
            'score': float(match.get('score', 0.0)),
            'metadata': {
                'company_id': metadata.get('company_id'),
                'page_type': metadata.get('page_type'),
                'token_count': metadata.get('token_count')
            }
        })

    return formatted_results