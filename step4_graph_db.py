import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 1. Load our secure credentials
load_dotenv()
URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")

class MemoryGraphDB:
    def __init__(self, uri, user, password):
        # Establish connection to Neo4j
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print("Successfully connected to Neo4j Database!")

    def close(self):
        self.driver.close()

    def ingest_data(self, json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        with self.driver.session() as session:
            print("Creating Entities (Nodes) in the Graph...")
            for entity in data["entities"]:
                # MERGE ensures we don't create duplicates if we run this twice!
                session.execute_write(self._create_entity, entity)

            print("Creating Claims (Relationships) in the Graph...")
            for claim in data["claims"]:
                session.execute_write(self._create_claim, claim)
                
        print(f"Successfully ingested {len(data['entities'])} entities and {len(data['claims'])} claims into Neo4j!")

    @staticmethod
    def _create_entity(tx, entity):
        # Cypher query to create or update a Node
        query = """
        MERGE (e:Entity {id: $id})
        SET e.name = $name, 
            e.type = $type, 
            e.aliases = $aliases
        """
        tx.run(query, id=entity["id"], name=entity["name"], type=entity["type"], aliases=entity["aliases"])

    @staticmethod
    def _create_claim(tx, claim):
        # In Cypher, relationship types cannot be parameterized dynamically, so we inject it safely using f-strings
        # We also convert the evidence list into a string so it can be stored on the relationship edge
        relation_type = claim["relation"].replace(" ", "_").upper()
        evidence_str = json.dumps(claim["evidence"])

        query = f"""
        MATCH (sub:Entity {{id: $sub_id}})
        MATCH (obj:Entity {{id: $obj_id}})
        MERGE (sub)-[rel:{relation_type}]->(obj)
        SET rel.evidence = $evidence
        """
        tx.run(query, sub_id=claim["subject_id"], obj_id=claim["object_id"], evidence=evidence_str)

if __name__ == "__main__":
    # Initialize the database connection
    db = MemoryGraphDB(URI, USERNAME, PASSWORD)
    
    # Run the ingestion pipeline
    try:
        db.ingest_data("canonicalized_memory.json")
    finally:
        db.close()