"""Deterministic browser fixtures, never available to the production application."""

import hashlib
import json
import re

from pydantic import BaseModel

from jobhunter_api.inference import Completion
from jobhunter_api.job_parser import ParsedJob
from jobhunter_api.store import Row


class BrowserFixtureProvider:
    def complete(
        self, model: str, prompt: str, data: str, schema: type[BaseModel], max_output: int
    ) -> Completion:
        payload = json.loads(data)
        if schema is ParsedJob:
            result: Row = {
                field: {"value": None, "quote": None, "confidence": 0}
                for field in ParsedJob.model_fields
                if field not in {"requirements", "risk_flags"}
            }
            for field, value in {
                "title": "Junior Python Developer",
                "location": "Dublin",
                "company_name": "Example Labs",
                "seniority": "junior",
            }.items():
                quote = "Junior" if field == "seniority" else value
                assert quote in payload["raw_text"]
                result[field] = {"value": value, "quote": quote, "confidence": 0.9}
            result.update(
                requirements=[
                    {
                        "text": "Python",
                        "category": "technical_skills",
                        "importance": "required",
                        "is_eliminatory": False,
                        "future_authorisation": False,
                        "quote": "Python is required.",
                        "confidence": 0.9,
                    }
                ],
                risk_flags=[],
            )
        else:
            fact, evidence = payload["facts"][0], payload["evidence"][0]
            result = {
                "assessments": [
                    {
                        "requirement_id": requirement["id"],
                        "status": "met",
                        "reason": (
                            "Projeto Python documentado; experiência comercial não declarada."
                        ),
                        "confidence": 0.8,
                        "citations": [
                            {
                                "fact_id": fact["id"],
                                "evidence_id": evidence["id"],
                                "fact_quote": fact["claim"],
                                "evidence_quote": evidence["content"],
                            }
                        ],
                    }
                    for requirement in payload["requirements"]
                ],
                "limitations": ["Fixture de teste."],
            }
        return Completion(json.dumps(result), 100, 100, "browser-fixture", 5, "completed")

    def embed(self, texts: list[str]) -> Completion:
        vectors = []
        for text in texts:
            vector = [0.0] * 256
            for word in re.findall(r"\w+", text.casefold()):
                vector[hashlib.sha256(word.encode()).digest()[0]] += 1
            vectors.append(vector)
        return Completion(
            json.dumps({"vectors": vectors}), 20, 0, "browser-fixture", 5, "completed"
        )
