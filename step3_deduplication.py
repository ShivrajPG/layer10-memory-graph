import json

def deduplicate_memory():
    # 1. Load the raw extracted memory from Step 2
    with open("extracted_memory.json", "r", encoding="utf-8") as f:
        memory_data = json.load(f)

    global_entities = {}
    global_claims = {}

    print("Starting Deduplication and Canonicalization Pipeline...")

    for issue in memory_data:
        
        # --- A. ENTITY CANONICALIZATION ---
        for entity in issue["entities"]:
            # Rule 1: Normalize IDs to lowercase and strip whitespace so "Shivraj" == "shivraj"
            raw_id = str(entity["id"])
            canonical_id = raw_id.strip().lower()

            if canonical_id not in global_entities:
                # Create a new canonical entity
                global_entities[canonical_id] = {
                    "id": canonical_id,
                    "type": entity["type"].upper(),
                    "name": entity["name"],
                    "aliases": set([raw_id, entity["name"]]) # Use a Set to automatically prevent duplicate aliases
                }
            else:
                # If it already exists, just add the new names to its aliases list
                global_entities[canonical_id]["aliases"].add(raw_id)
                global_entities[canonical_id]["aliases"].add(entity["name"])

        # --- B. CLAIM DEDUPLICATION ---
        for claim in issue["claims"]:
            sub_id = str(claim["subject_id"]).strip().lower()
            rel = str(claim["relation"]).upper()
            obj_id = str(claim["object_id"]).strip().lower()

            # Rule 2: Create a unique signature for this claim
            claim_key = f"{sub_id}-[{rel}]->{obj_id}"

            if claim_key not in global_claims:
                # Create a new claim
                global_claims[claim_key] = {
                    "subject_id": sub_id,
                    "relation": rel,
                    "object_id": obj_id,
                    "evidence": claim["evidence"] # Start with the evidence list from this issue
                }
            else:
                # Rule 3: Merge Evidence!
                # If the claim already exists, do NOT create a new claim.
                # Instead, attach the new evidence to the existing claim so we don't lose the source.
                existing_evidence_urls = [e["url"] for e in global_claims[claim_key]["evidence"]]
                
                for ev in claim["evidence"]:
                    # Prevent duplicate evidence links
                    if ev["url"] not in existing_evidence_urls:
                        global_claims[claim_key]["evidence"].append(ev)

    # Convert our Python Sets back to Lists so we can save it as JSON
    for ent in global_entities.values():
        ent["aliases"] = list(ent["aliases"])

    # Prepare final clean data
    final_graph = {
        "entities": list(global_entities.values()),
        "claims": list(global_claims.values())
    }

    # Save to our new pristine JSON file
    with open("canonicalized_memory.json", "w", encoding="utf-8") as f:
        json.dump(final_graph, f, indent=4)

    print(f"Success! Canonicalized down to {len(final_graph['entities'])} unique entities and {len(final_graph['claims'])} unique claims.")

if __name__ == "__main__":
    deduplicate_memory()