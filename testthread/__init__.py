import requests

class TestThread:
    def __init__(self, base_url="https://test-thread-production.up.railway.app", gemini_key=None):
        self.base = base_url.rstrip("/")
        self.gemini_key = gemini_key

    def create_suite(self, name, agent_endpoint, description=None, webhook_url=None):
        res = requests.post(f"{self.base}/suites", json={
            "name": name,
            "description": description,
            "agent_endpoint": agent_endpoint,
            "webhook_url": webhook_url
        })
        return res.json()

    def add_case(self, suite_id, name, input, expected_output, match_type="contains", description=None):
        res = requests.post(f"{self.base}/suites/{suite_id}/cases", json={
            "name": name,
            "description": description,
            "input": input,
            "expected_output": expected_output,
            "match_type": match_type
        })
        return res.json()

    def run_suite(self, suite_id):
        params = {}
        if self.gemini_key:
            params["gemini_key"] = self.gemini_key
        res = requests.post(f"{self.base}/suites/{suite_id}/run", params=params)
        return res.json()

    def diagnose(self, input, expected_output, actual_output):
        res = requests.post(f"{self.base}/diagnose", json={
            "input": input,
            "expected_output": expected_output,
            "actual_output": actual_output,
            "api_key": self.gemini_key
        })
        return res.json()

    def get_run(self, run_id):
        res = requests.get(f"{self.base}/runs/{run_id}")
        return res.json()

    def list_suites(self):
        res = requests.get(f"{self.base}/suites")
        return res.json()

    def list_runs(self):
        res = requests.get(f"{self.base}/runs")
        return res.json()

    def stats(self):
        res = requests.get(f"{self.base}/dashboard/stats")
        return res.json()