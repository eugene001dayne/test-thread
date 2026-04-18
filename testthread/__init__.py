"""
TestThread Python SDK — v0.12.0
pytest for AI agents.
"""
import httpx
from typing import Optional


class TestThread:
    def __init__(
        self,
        base_url: str = "https://test-thread.onrender.com",
        gemini_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.gemini_key = gemini_key
        self._client = httpx.Client(base_url=self.base_url, timeout=60)

    def _post(self, path: str, json: dict = None):
        r = self._client.post(path, json=json or {})
        r.raise_for_status()
        return r.json()

    def _get(self, path: str):
        r = self._client.get(path)
        r.raise_for_status()
        return r.json()

    # ── Suites ──────────────────────────────────────────────────────────────

    def create_suite(self, name: str, agent_endpoint: str, description: str = None, webhook_url: str = None):
        return self._post("/suites", {
            "name": name,
            "agent_endpoint": agent_endpoint,
            "description": description,
            "webhook_url": webhook_url,
        })

    def list_suites(self):
        return self._get("/suites")

    # ── Cases ────────────────────────────────────────────────────────────────

    def add_case(
        self,
        suite_id: str,
        name: str,
        input: str,
        expected_output: str,
        match_type: str = "contains",
        description: str = None,
        source: str = "manual",
    ):
        return self._post(f"/suites/{suite_id}/cases", {
            "name": name,
            "input": input,
            "expected_output": expected_output,
            "match_type": match_type,
            "description": description,
            "source": source,
        })

    def list_cases(self, suite_id: str):
        return self._get(f"/suites/{suite_id}/cases")

    # ── Run ──────────────────────────────────────────────────────────────────

    def run_suite(self, suite_id: str):
        return self._post(f"/suites/{suite_id}/run", {"gemini_key": self.gemini_key})

    # ── Adversarial generation (v0.11.0) ─────────────────────────────────────

    def generate_adversarial(self, suite_id: str, count: int = 5, focus: str = "edge_cases"):
        """
        Generate adversarial test cases for a suite using Gemini.
        Returns cases ready for review — nothing is saved automatically.
        focus: 'safety' | 'accuracy' | 'edge_cases' | 'contradictions'
        """
        return self._post(f"/suites/{suite_id}/generate-adversarial", {
            "count": count,
            "focus": focus,
        })

    # ── Production monitoring (v0.12.0) ──────────────────────────────────────

    def monitor(self, suite_id: str, input: str, actual_output: str):
        """
        Submit a real production interaction for continuous behavioral drift detection.
        """
        return self._post("/monitor", {
            "suite_id": suite_id,
            "input": input,
            "actual_output": actual_output,
        })

    def get_drift(self, suite_id: str):
        """
        Get drift events and rolling pass rate trend for a suite.
        """
        return self._get(f"/monitor/{suite_id}/drift")

    # ── Schedule ─────────────────────────────────────────────────────────────

    def set_schedule(self, suite_id: str, schedule: str, enabled: bool = True):
        return self._post(f"/suites/{suite_id}/schedule", {
            "schedule": schedule,
            "schedule_enabled": enabled,
        })

    def get_schedule(self, suite_id: str):
        return self._get(f"/suites/{suite_id}/schedule")

    # ── Diagnose ─────────────────────────────────────────────────────────────

    def diagnose(self, input: str, expected_output: str, actual_output: str):
        return self._post("/diagnose", {
            "input": input,
            "expected_output": expected_output,
            "actual_output": actual_output,
        })

    # ── Runs ─────────────────────────────────────────────────────────────────

    def get_run(self, run_id: str):
        return self._get(f"/runs/{run_id}")

    def list_runs(self):
        return self._get("/runs")

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self):
        return self._get("/dashboard/stats")

    def health(self):
        return self._get("/")