# Layer10 Memory Graph System

An enterprise-grade, grounded organizational memory system. This pipeline ingests unstructured and structured data (GitHub issues/comments), uses LLMs to extract relational claims, canonicalizes entities to deduplicate assertions, and pushes the resulting knowledge graph to Neo4j.

---

## I. System Architecture

![Layer10_memory_system (4)](https://github.com/user-attachments/assets/e7576fce-ffd1-4b29-af69-f06a373e218f)

The system is designed with a clear separation between the Minimum Viable Product (MVP) built for this assignment (represented by solid lines) and the Layer10 Enterprise Scaling vision (represented by dotted lines).

### a. The Data Ingestion Layer
* **MVP Scope:** The system currently ingests unstructured chat (comments) and structured metadata (issues) from the `langchain-ai` GitHub API via `step1_ingestion.py`.
* **Enterprise Scaling:** The ingestion pipeline is modular. As shown in the diagram, enterprise sources like **Slack APIs (Chat), Jira (Tickets), and Email/Docs** can be seamlessly routed into the same extraction engine to build a unified organizational memory.

### b. The Extraction & Deduplication Layer
* **Extraction (`step2_extraction.py`):** Uses Groq (Llama-3.3) and Pydantic to enforce a strict ontology. Crucially, a programmatic Python safety net validates that every excerpt is a perfect substring of the raw text, guaranteeing 100% grounding.
* **Canonicalization (`step3_deduplication.py`):** A deterministic deduplication engine normalizes IDs, aggregates aliases, and safely merges evidence payloads across duplicate claims.

### c. Polyglot Persistence (Storage Layer)
* **MVP Scope:** Extracted canonical entities and grounded claims are pushed to **Neo4j Aura Cloud** as an explorable Graph Database.
* **Enterprise Scaling:** While Neo4j excels at relational mapping, storing massive unstructured chat histories (like years of Slack logs) directly on graph edges is inefficient. In production, I would adopt a **Polyglot Persistence** architecture (shown via dotted lines), utilizing Neo4j for the relational graph and a **Vector/Document DB** for storing raw artifacts and enabling dense semantic search.

---

## II. Ontology & Extraction Contract

The system relies on a strict, programmatic extraction contract defined via Pydantic:
* **Entities:** Are strictly typed (`USER`, `ISSUE`, `COMPONENT`, `CONCEPT`). Each entity requires a normalized `id` and `name`.
* **Claims:** Must take the form of `subject_id` ➡️ `relation` ➡️ `object_id`. Relations are restricted via enums (e.g., `REPORTED`, `RESOLVED`).
* **Grounding & Safety:** Every single claim requires an `Evidence` object containing the `source_id`, `url`, `timestamp`, and an **exact excerpt string**.
* **Validation & Repair (Quality Gates):** The LLM is forced to output a `confidence_score` (0.0 to 1.0) for every claim. Claims scoring `< 0.8` are instantly pruned. Furthermore, a strict Python verification function (`raw_text.find(excerpt)`) mathematically proves the excerpt is a perfect substring of the source artifact. If the LLM hallucinates, the claim is dropped.

---

## III. Deduplication & Canonicalization Strategy

Redundant facts (e.g., multiple users commenting on the same bug) are handled gracefully to prevent graph pollution:
1. **Entity Canonicalization:** Entities are resolved by standardizing IDs (lowercase, stripped whitespace). An `aliases` set groups variations of a single entity (e.g., "Shivraj" and "shivraj_g" merge into one node).
2. **Claim Deduplication:** Claims are signature-matched via `(Subject)-[Relation]->(Object)`. When a duplicate relational claim is found, the system **does not overwrite the claim**. Instead, it safely **merges the Evidence arrays**, ensuring that multiple citations pointing to the exact same fact are preserved on a single canonical edge.
3. **Update Semantics (Idempotency):** The ingestion script (`step4_graph_db.py`) uses Cypher `MERGE` commands exclusively. Running the pipeline continuously on the same data safely updates aliases and evidence arrays without duplicating graph topography.

---

## IV. Retrieval and Grounding

The Agentic UI (`step5_ui.py`) translates natural language into verified answers using the following retrieval mechanics:

* **Mapping Questions to Entities:** A deterministic Python layer maps conversational synonyms to the strict ontology (e.g., translating the word "bugs" to the edge type `[:REPORTED]` or node type `(:ISSUE)`). The resulting terms are queried via an optimized Cypher `CONTAINS` match across Node Names, Aliases, and Edge Types.
* **Expand/Aggregate without Exploding:** The graph prevents explosion during retrieval in two ways. First, data is heavily pruned at ingestion via the >0.8 confidence Quality Gate. Second, graph traversals are strictly bounded via Cypher `LIMIT` clauses to fetch only the highest-relevance 1-hop neighborhoods.
* **Ensuring Grounding & Citation Formatting:** The retrieved graph edges (the "Context Pack") are flattened into a string payload. The LLM prompt strictly enforces inline citations `[Citation X]`. The UI then dynamically generates expandable Markdown blocks so users can click through to the exact GitHub URL and read the raw, verified quote.
* **Handling Ambiguity & Conflicting Sources:** By preserving all supporting evidence arrays during the Deduplication phase, the retrieval engine possesses a true timeline of facts. If the database contains temporal conflicts (e.g., an issue was "resolved" but later "reopened"), the Context Pack passes all chronologically-ordered evidence edges to the LLM. The LLM is system-prompted to synthesize the ambiguity, explicitly citing both the historical and current state of truth, keeping the human in the loop.

---

## V. Layer10 Considerations (Enterprise Adaptation)

To adapt this MVP for Layer10’s target environment (Slack, Teams, Jira, Email), the architecture must scale:

* **Unstructured + Structured Fusion:** 
  Jira and Linear tickets would be modeled as structural `(:Artifact)` nodes. Unstructured Slack/Teams threads discussing those tickets would be extracted and explicitly connected via `(:SlackThread)-[REFERS_TO]->(:Artifact)` relationships, bridging conversational context to formal tracking systems.
* **Long-Term Memory vs. Ephemeral Context:** 
  To prevent graph drift from daily casual chat, "Ephemeral Context" (Slack chatter) would be held in a temporary vector store. A nightly LLM cron-job would evaluate this context; only finalized decisions or high-confidence facts would be promoted into durable `(:Claim)` edges in the Memory Graph.
* **Permissions (RBAC):** 
  Memory retrieval must be constrained by underlying access. In production, graph edges would store an Access Control List (ACL) ID on the Artifact. Cypher queries would be dynamically scoped via graph traversal: 
  `MATCH (s:Entity)-[c:CLAIM]->(o:Entity)-[:SUPPORTED_BY]->(a:Artifact) WHERE a.acl_id IN $user_permissions RETURN c`
  This ensures users never retrieve claims generated from private channels they cannot access.
* **Grounding & Safety (Deletions/Redactions):** 
  If an email or Slack message is deleted for privacy/GDPR, its source `(:Artifact)` must be hard-deleted. A cascading tombstone mechanism would trigger: any `(:Claim)` edge that loses all of its supporting `Evidence` pointers due to a redaction is automatically tombstoned to prevent retrieving facts from phantom sources.
* **Operational Reality & Scaling:** 
  * *Streaming vs Batch:* The sequential ingestion loop must be replaced with Kafka/Pulsar streams for highly parallelized LLM extraction. However, to prevent race conditions when generating global Entity IDs, the Canonicalization phase must be linearly queued or handled via strictly enforced Graph Database locking mechanisms.
  * *Cost:* To optimize costs, a smaller, fine-tuned model (e.g., Llama-3-8B) would handle structured extraction, while a heavier model (GPT-4o/Claude-3.5) would handle the final UI synthesis.

---

## VI Example Graph Queries

To test the capabilities of the Agentic UI and the underlying Neo4j graph, you can run the following natural language queries in the Streamlit interface:

1. **Semantic Search:** `"What bugs or issues were resolved?"`
2. **Entity Aggregation:** `"Summarize everything codspeed-hq[bot] reported."`
3. **Component Deep-Dive:** `"Were there any fixes proposed for openai or gpt-5.4 models?"`
4. **Temporal State Tracking:** `"Were there any state changes regarding inf-0000 or ci(infra)?"`
5. **Anti-Hallucination Gate:** `"What did Sam Altman say about the LangChain classic package?"` 
<img width="1895" height="905" alt="Screenshot 2026-03-07 024526" src="https://github.com/user-attachments/assets/ff3e522e-4837-4fc7-afa7-76d264704cd4" />
<img width="1883" height="903" alt="Screenshot 2026-03-07 024506" src="https://github.com/user-attachments/assets/01e9a0f5-0e15-4be4-8d52-6407e97f626c" />
<img width="1894" height="901" alt="Screenshot 2026-03-07 024444" src="https://github.com/user-attachments/assets/4df2b61d-5d73-47d6-b5f5-bcca67f02808" />
<img width="1864" height="899" alt="Screenshot 2026-03-07 024414" src="https://github.com/user-attachments/assets/52095b16-bfc1-4f32-b37b-dc8dd53b1c0b" />
<img width="1887" height="896" alt="Screenshot 2026-03-07 024256" src="https://github.com/user-attachments/assets/20eea756-825e-46f4-97f6-06bb200f835a" />

<img width="1900" height="908" alt="Screenshot 2026-03-07 024559" src="https://github.com/user-attachments/assets/ebcd13e5-2141-4726-b093-1a640787a902" />

---

## VII. Reproducibility & Setup

### Prerequisites
* Python 3.10+
* A Neo4j Database instance (Aura Cloud)
* Groq API Key
* GitHub API Token

### a. Clone & Install Dependencies
Open a terminal in the project directory and run:
```bash
python -m venv venv
source venv/bin/activate 
pip install -r requirements.txt
```

### b. Configure Environment Variables
Create a .env file in the root directory and add your credentials:
```bash
GROQ_API_KEY="your_groq_api_key"
NEO4J_URI=
NEO4J_USERNAME=
NEO4J_PASSWORD=
GITHUB_TOKEN="your_github_token"
```

### c. Execute the End-to-End Pipeline
Run the numbered scripts sequentially to move data from raw text into the Memory Graph:
```bash
python step1_ingestion.py       # Pulls raw data from GitHub API
python step2_extraction.py      # LLM extraction & Quality Gates
python step3_deduplication.py   # Canonicalization and Evidence Merging
python step4_graph_db.py        # Pushes knowledge to Neo4j
```

### d. Launch the User Interface
```bash
streamlit run step5_ui.py

```
This starts an interactive dashboard running on localhost where you can question the memory graph via the Agentic QA tab, or explore the raw PyVis visualization.
