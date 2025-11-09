# Workflow Graph (Placeholder)

```mermaid
flowchart TD
    A[Planner Node] --> B[Data Generation Node]
    B --> C[Evaluation Node]
    C -->|Risk detected| D[HITL Node]
    C -->|No risk| E[Auto-approve + Save]
    D --> E