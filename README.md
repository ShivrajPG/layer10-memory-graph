# 🧠 Layer10 Take-Home: Grounded Memory Graph System

This repository implements a production-grade, long-term memory graph system. It ingests unstructured communication (GitHub Issues and comments) and structures them into deduplicated Entities and Claims using Large Language Models, storing them in a queryable Neo4j graph.

## 🌟 Core Features & Rubric Fulfillment

- **Strict Grounding Verifier:** Every extracted claim is programmatically validated via Python (`original_text.find()`) to ensure the LLM's evidence string exists as a perfect substring in the source text. Hallucinations are actively dropped.
- **Canonicalization:** Entities are deduplicated using ID normalization and alias aggregation. 
- **Claim Resolution:** If identical assertions are made across multiple issues, they are merged. The new evidence references are safely appended to the canonical claim.
- **Agentic GraphRAG Retrieval:** Translates natural language into a graph query, retrieves a Grounded Context Pack from Neo4j, and synthesizes a concise response with inline citations.

---

## 🏛️ System Architecture

```mermaid
graph TD
    %% Define Styles
    classDef llm fill:#f9f,stroke:#333,stroke-width:2px;
    classDef db fill:#bbf,stroke:#333,stroke-width:2px;
    classDef script fill:#cfc,stroke:#333,stroke-width:2px;
    classDef ui fill:#fcf,stroke:#333,stroke-width:2px;

    %% Nodes
    A[GitHub API] -->|Raw JSON| B(1_ingestion.py):::script
    B -->|Unstructured Text| C{Groq Llama-3 + Pydantic}:::llm
    C -->|Entities & Claims| D(2_extraction.py + Grounding Verifier):::script
    D -->|Validated JSON| E(3_deduplication.py):::script
    E -->|Canonicalized Data| F[(Neo4j Cloud Aura DB)]:::db
    
    %% User Flow
    User((User)) -->|Natural Language Query| G[5_ui.py Streamlit]:::ui
    G -->|Query Translation| H{Groq Llama-3}:::llm
    H -->|Graph Search| F
    F -->|Grounded Context Pack| I{Groq Synthesis}:::llm
    I -->|GraphRAG Answer + Citations| User
