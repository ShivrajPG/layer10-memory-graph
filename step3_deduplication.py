import json

def deduplicate_memory():
    with open("extracted_memory.json", "r", encoding="utf-8") as f:
        memory_data = json.load(f)

    global_entities = {}
    global_claims = {}
    print("Starting Deduplication and Canonicalization Pipeline...")

    for issue in memory_data:
        for entity in issue["entities"]:
            raw_id = str(entity["id"])
            canonical_id = raw_id.strip().lower()

            if canonical_id not in global_entities:
                global_entities[canonical_id] = {
                    "id": canonical_id,
                    "type": entity["type"].upper(),
                    "name": entity["name"],
                    "aliases": set([raw_id, entity["name"]]) 
                }
            else:
                global_entities[canonical_id]["aliases"].add(raw_id)
                global_entities[canonical_id]["aliases"].add(entity["name"])

        for claim in issue["claims"]:
            sub_id = str(claim["subject_id"]).strip().lower()
            rel = str(claim["relation"]).upper()
            obj_id = str(claim["object_id"]).strip().lower()

            claim_key = f"{sub_id}-[{rel}]->{obj_id}"

            if claim_key not in global_claims:
                global_claims[claim_key] = {
                    "subject_id": sub_id,
                    "relation": rel,
                    "object_id": obj_id,
                    "evidence": claim["evidence"] 
                }
            else:
                existing_evidence_urls = [e["url"] for e in global_claims[claim_key]["evidence"]]
                
                for ev in claim["evidence"]:
                    if ev["url"] not in existing_evidence_urls:
                        global_claims[claim_key]["evidence"].append(ev)

    for ent in global_entities.values():
        ent["aliases"] = list(ent["aliases"])

    final_graph = {
        "entities": list(global_entities.values()),
        "claims": list(global_claims.values())
    }

    with open("canonicalized_memory.json", "w", encoding="utf-8") as f:
        json.dump(final_graph, f, indent=4)

    print(f"Successfully Canonicalized down to {len(final_graph['entities'])} unique entities and {len(final_graph['claims'])} unique claims.")

if __name__ == "__main__":
    deduplicate_memory()
