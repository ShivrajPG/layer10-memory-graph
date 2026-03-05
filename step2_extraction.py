import os
import json
import time

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class Evidence(BaseModel):
    source_id: str = Field(description="The ID of the github issue or comment")
    excerpt: str = Field(description="Exact quote proving the claim")
    url: str = Field(description="URL pointing to the evidence")
    timestamp: str = Field(description="RUBRIC: Grounding - ISO 8601 Timestamp of when this evidence was created")

class Entity(BaseModel):
    id: str = Field(description="Unique identifier (e.g., username, issue number). LOWERCASE.")
    type: str = Field(description="MUST be: USER, ISSUE, COMPONENT, CONCEPT")
    name: str = Field(description="Display name")

class Claim(BaseModel):
    subject_id: str = Field(description="ID of the entity doing the action")
    relation: str = Field(description="MUST be: REPORTED, PROPOSED_FIX, CHANGED_STATE, RESOLVED")
    object_id: str = Field(description="ID of the entity receiving the action")
    evidence: List[Evidence] = Field(description="Quotes proving this relationship")
    confidence_score: float = Field(description="RUBRIC: Quality Gate - Float between 0.0 and 1.0 indicating confidence in this claim")

class ExtractionResult(BaseModel):
    entities: List[Entity] = Field(description="All entities extracted")
    claims: List[Claim] = Field(description="All relational claims extracted")


llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile", groq_api_key=GROQ_API_KEY)
structured_llm = llm.with_structured_output(ExtractionResult)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an elite AI extraction engine for organizational memory. "
               "Extract entities and claims from GitHub issues. "
               "RUBRIC RULES: "
               "1. Grounding: EVERY claim must have an exact excerpt and timestamp. "
               "2. State Changes: Pay close attention to who changed the state of an issue (e.g., closed it). "
               "3. Confidence: Assign a strict confidence score (0.0 to 1.0). If you are guessing, score it < 0.5. "
               "Do not hallucinate."),
    ("human", "Extract structured knowledge from this payload:\n\n{issue_data}")
])

extraction_chain = prompt | structured_llm


def run_extraction_with_retries(issue_text, max_retries=3):
    """RUBRIC: Validation & Repair - Handles invalid outputs via deterministic retries."""
    for attempt in range(max_retries):
        try:
            result = extraction_chain.invoke({"issue_data": issue_text})
            

            high_confidence_claims = [c for c in result.claims if c.confidence_score >= 0.8]
            
            if len(result.claims) != len(high_confidence_claims):
                print(f"Quality Gate: Dropped {len(result.claims) - len(high_confidence_claims)} low-confidence claims.")
                
            return result.entities, high_confidence_claims
            
        except Exception as e:
            print(f"[Attempt {attempt+1} Failed] Validation Error: {e}. Retrying...")
            time.sleep(2)
            
    print("Extraction failed after max retries. Emitting empty result to protect memory state.")
    return [],[]

def run_extraction():
    with open("corpus.json", "r", encoding="utf-8") as f:
        corpus = json.load(f)
    
    extraction_metadata = {
        "schema_version": "1.1.0",
        "model_version": "llama-3.3-70b-versatile",
        "timestamp": time.time()
    }
    
    extracted_memory =[]
    
    print("Starting Enterprise LLM Extraction Pipeline...")
    for issue in corpus: 
        print(f"Processing: {issue['title']}...")
     
        issue_text = f"Title: {issue['title']}\nState: {issue['state']}\nCreated At: {issue['created_at']}\nBody: {issue['body']}\n"
        for comment in issue['comments']:
            issue_text += f"\nComment by {comment['user']} at {comment['created_at']}: {comment['body']}"
      
        entities, valid_claims = run_extraction_with_retries(issue_text)
        
        extracted_memory.append({
            "source_issue": issue['source_id'],
            "extraction_metadata": extraction_metadata,
            "entities": [e.model_dump() for e in entities],
            "claims":[c.model_dump() for c in valid_claims]
        })
        print(f"Extracted {len(entities)} entities and {len(valid_claims)} valid claims.")

    with open("extracted_memory.json", "w", encoding="utf-8") as f:
        json.dump(extracted_memory, f, indent=4)
    print(f"\n Saved extracted data to extracted_memory.json")

if __name__ == "__main__":
    run_extraction()
