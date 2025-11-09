# ReAct Trace Example (Placeholder)

Paste a real ReAct trace here once your Supervisor Agent logs Thought → Action → Observation steps. Something like..

Thought: I should fetch the latest structured payload.
Action: get_latest_structured_payload(company_id="...")
Observation: {...payload json...}
Thought: I should search RAG for potential layoffs.
Action: rag_search_company(company_id="...", query="layoffs OR workforce reduction")
Observation: Found 1 article referencing layoffs in 2024.
Thought: I should call report_layoff_signal with a LayoffSignal object.