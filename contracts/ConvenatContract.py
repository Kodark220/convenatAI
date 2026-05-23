# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class JobTerms:
    buyer_agent_id: str
    seller_agent_id: str
    description: str
    is_active: bool
    expected_quality_criteria: str
    deliverable_uri: str


class ConvenatContract(gl.Contract):
    jobs: TreeMap[str, JobTerms]

    def __init__(self):
        pass

    @gl.public.write
    def register_job(
        self,
        stream_id: str,
        buyer_id: str,
        seller_id: str,
        description: str,
        quality_criteria: str,
        deliverable_uri: str = "",
    ) -> None:
        self.jobs[stream_id] = JobTerms(
            buyer_agent_id=buyer_id,
            seller_agent_id=seller_id,
            description=description,
            expected_quality_criteria=quality_criteria,
            deliverable_uri=deliverable_uri,
            is_active=True,
        )

    def _evaluate_evidence(self, deliverable_uri: str, criteria: str) -> dict:
        def get_evaluation_result() -> str:
            deliverable_data = gl.nondet.web.get(deliverable_uri, mode="text")
            task = f"""
            You are a strict, objective Quality Assurance AI.
            Evaluate the following deliverable against the criteria.

            CRITERIA: {criteria}
            DELIVERABLE DATA: {deliverable_data}

            Respond in valid JSON only:
            {{"meets_criteria": true, "reasoning": "brief explanation"}}
            """
            result = gl.nondet.exec_prompt(task, response_format="json")
            return json.dumps(result, sort_keys=True)

        result_json = json.loads(gl.eq_principle.strict_eq(get_evaluation_result))
        return result_json

    @gl.public.write
    def monitor_stream(self, stream_id: str, deliverable_uri: str) -> None:
        if stream_id not in self.jobs:
            raise Exception("Job stream not found.")

        job = self.jobs[stream_id]
        if not job.is_active:
            raise Exception("Job stream is already terminated.")

        if deliverable_uri:
            job.deliverable_uri = deliverable_uri

        eval_result = self._evaluate_evidence(
            job.deliverable_uri or deliverable_uri,
            job.expected_quality_criteria,
        )

        meets_criteria = eval_result.get("meets_criteria", False)
        if isinstance(meets_criteria, str):
            meets_criteria = meets_criteria.lower() in ("true", "yes", "1")

        if not meets_criteria:
            job.is_active = False

    @gl.public.view
    def get_job_status(self, stream_id: str) -> dict:
        if stream_id not in self.jobs:
            raise Exception("Job stream not found.")
        job = self.jobs[stream_id]
        return {
            "buyer": job.buyer_agent_id,
            "seller": job.seller_agent_id,
            "active": job.is_active,
            "description": job.description,
            "criteria": job.expected_quality_criteria,
            "deliverable_uri": job.deliverable_uri,
        }
