import uuid
import httpx
import re
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from supabase import create_client, Client
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://oigfsomrrmoditnrjgdm.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pZ2Zzb21ycm1vZGl0bnJqZ2RtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NzY3NTYsImV4cCI6MjA4OTQ1Mjc1Nn0.TPLvSzRxUMKYB-vhJa204UOv6nCI8CBx9mAmqNP7BAU")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="TestThread", description="pytest for AI agents", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SuiteCreate(BaseModel):
    name: str
    description: Optional[str] = None
    agent_endpoint: str

class CaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    input: str
    expected_output: str
    match_type: str = "contains"

@app.get("/")
def root():
    return {"name": "TestThread", "version": "0.1.0", "status": "running"}

@app.post("/suites")
def create_suite(suite: SuiteCreate):
    suite_id = str(uuid.uuid4())
    data = {
        "id": suite_id,
        "name": suite.name,
        "description": suite.description,
        "agent_endpoint": suite.agent_endpoint,
    }
    result = supabase.table("test_suites").insert(data).execute()
    return result.data[0]

@app.get("/suites")
def list_suites():
    result = supabase.table("test_suites").select("*").order("created_at", desc=True).execute()
    return result.data

@app.post("/suites/{suite_id}/cases")
def add_case(suite_id: str, case: CaseCreate):
    case_id = str(uuid.uuid4())
    data = {
        "id": case_id,
        "suite_id": suite_id,
        "name": case.name,
        "description": case.description,
        "input": case.input,
        "expected_output": case.expected_output,
        "match_type": case.match_type,
    }
    result = supabase.table("test_cases").insert(data).execute()
    return result.data[0]

@app.get("/suites/{suite_id}/cases")
def list_cases(suite_id: str):
    result = supabase.table("test_cases").select("*").eq("suite_id", suite_id).execute()
    return result.data

@app.post("/suites/{suite_id}/run")
async def run_suite(suite_id: str):
    suite_result = supabase.table("test_suites").select("*").eq("id", suite_id).execute()
    if not suite_result.data:
        raise HTTPException(status_code=404, detail="Suite not found")
    suite = suite_result.data[0]

    cases_result = supabase.table("test_cases").select("*").eq("suite_id", suite_id).execute()
    cases = cases_result.data

    if not cases:
        raise HTTPException(status_code=400, detail="No test cases in this suite")

    run_id = str(uuid.uuid4())
    supabase.table("test_runs").insert({
        "id": run_id,
        "suite_id": suite_id,
        "status": "running",
        "total": len(cases),
        "passed": 0,
        "failed": 0,
    }).execute()

    passed = 0
    failed = 0
    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for case in cases:
            try:
                response = await client.post(
                    suite["agent_endpoint"],
                    json={"input": case["input"]},
                    headers={"Content-Type": "application/json"}
                )
                actual = response.text
                expected = case["expected_output"]
                match_type = case.get("match_type", "contains")

                if match_type == "exact":
                    success = actual.strip() == expected.strip()
                elif match_type == "regex":
                    success = bool(re.search(expected, actual))
                else:
                    success = expected.lower() in actual.lower()

                status = "passed" if success else "failed"
                reason = None if success else f"Expected '{expected}' not found in output"

            except Exception as e:
                status = "failed"
                actual = None
                reason = str(e)

            if status == "passed":
                passed += 1
            else:
                failed += 1

            result_data = {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "case_id": case["id"],
                "case_name": case["name"],
                "status": status,
                "actual_output": actual[:1000] if actual else None,
                "reason": reason,
            }
            supabase.table("test_results").insert(result_data).execute()
            results.append(result_data)

    supabase.table("test_runs").update({
        "status": "completed",
        "passed": passed,
        "failed": failed,
        "completed_at": datetime.utcnow().isoformat(),
    }).eq("id", run_id).execute()

    return {
        "run_id": run_id,
        "total": len(cases),
        "passed": passed,
        "failed": failed,
        "status": "completed",
        "results": results
    }

@app.get("/runs")
def list_runs():
    result = supabase.table("test_runs").select("*").order("created_at", desc=True).execute()
    return result.data

@app.get("/runs/{run_id}")
def get_run(run_id: str):
    run = supabase.table("test_runs").select("*").eq("id", run_id).execute()
    if not run.data:
        raise HTTPException(status_code=404, detail="Run not found")
    results = supabase.table("test_results").select("*").eq("run_id", run_id).execute()
    return {**run.data[0], "results": results.data}

@app.get("/dashboard/stats")
def dashboard_stats():
    runs = supabase.table("test_runs").select("*").execute()
    suites = supabase.table("test_suites").select("*").execute()
    cases = supabase.table("test_cases").select("*").execute()

    total_passed = sum(r["passed"] for r in runs.data)
    total_failed = sum(r["failed"] for r in runs.data)

    return {
        "total_suites": len(suites.data),
        "total_cases": len(cases.data),
        "total_runs": len(runs.data),
        "total_passed": total_passed,
        "total_failed": total_failed,
        "pass_rate": round(total_passed / (total_passed + total_failed) * 100, 1) if (total_passed + total_failed) > 0 else 0
    }