import os
import json

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
URI = os.getenv("NEO4J_URI")
Username = os.getenv("NEO4J_USERNAME")
Password = os.getenv("NEO4J_PASSWORD")

class MemoryGraphDB:
    def __init__(self, uri, user, password):
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
                session.execute_write(self._create_entity, entity)

            print("Creating Claims (Relationships) in the Graph...")
            for claim in data["claims"]:
                session.execute_write(self._create_claim, claim)
                
        print(f"Successfully ingested {len(data['entities'])} entities and {len(data['claims'])} claims into Neo4j!")

    @staticmethod
    def _create_entity(tx, entity):

        query = """
        MERGE (e:Entity {id: $id})
        SET e.name = $name, 
            e.type = $type, 
            e.aliases = $aliases
        """
        tx.run(query, id=entity["id"], name=entity["name"], type=entity["type"], aliases=entity["aliases"])

    @staticmethod
    def _create_claim(tx, claim):

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

    db = MemoryGraphDB(URI, Username, Password)
    
    try:
        db.ingest_data("canonicalized_memory.json")
    finally:
        db.close()

        
