"""
interaction_agent.py
----------------------
Stage 2 of the pipeline: the safety net. Cross-checks every newly
prescribed medication against both the other new medications AND the
patient's existing medication list, using a curated interaction database.

This is deliberately a separate, deterministic-first agent (not just an
LLM call) precisely because false negatives here are the highest-stakes
failure mode in the whole system.
"""

import json
import os

from .base import Agent

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "drug_interactions.json")


class DrugInteractionAgent(Agent):
    name = "interaction_agent"

    def __init__(self, simulate: bool = False, db_path: str = DB_PATH):
        super().__init__(simulate=simulate)
        with open(db_path, "r") as f:
            self._db = json.load(f)["interactions"]

    def run(self, new_medications: list[dict], existing_medications: list[str]) -> dict:
        new_names = [m["name"].lower().strip() for m in new_medications]
        existing_names = [m.lower().strip() for m in existing_medications]
        all_names = new_names + existing_names

        warnings = []
        checked_pairs = set()

        for i, drug_a in enumerate(all_names):
            for drug_b in all_names[i + 1:]:
                pair_key = tuple(sorted((drug_a, drug_b)))
                if drug_a == drug_b or pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                match = self._lookup(drug_a, drug_b)
                if match:
                    warnings.append(
                        {
                            "drugs": [drug_a, drug_b],
                            "severity": match["severity"],
                            "description": match["description"],
                        }
                    )

        warnings.sort(key=lambda w: {"high": 0, "medium": 1, "low": 2}[w["severity"]])

        return {
            "warnings": warnings,
            "highest_severity": warnings[0]["severity"] if warnings else "none",
            "safe_to_proceed": not any(w["severity"] == "high" for w in warnings),
        }

    def _lookup(self, drug_a: str, drug_b: str):
        for entry in self._db:
            pair = {entry["drug_a"], entry["drug_b"]}
            if pair == {drug_a, drug_b}:
                return entry
        return None
