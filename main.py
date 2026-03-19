import uuid
import httpx
import re
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from supabase import create_client, Client
import os
PII_PATTERNS = {
    "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "phone": r"\b(\+?1?\s?)?(\(?\d{3}\)?[\s.-]?)(\d{3}[\s.-]?\d{4})\b",
    "credit_card": r"\b(?:\d{4}[\s-]?){3}\d{4}\b",
    "api_key": r"\b[A-Za-z0-9]{32,45}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
}

def detect_pii(text: str) -> dict:
    if not text:
        return {"detected": False, "types": []}
    found = []
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, text):
            found.append(pii_type)
    return {"detected": len(found) > 0, "types": found}

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://oigfsomrrmoditnrjgdm.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pZ2Zzb21ycm1vZGl0bnJqZ2RtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NzY3NTYsImV4cCI6MjA4OTQ1Mjc1Nn0.TPLvSzRxUMKYB-vhJa204UOv6nCI8CBx9mAmqNP7BAU")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="TestThread", description="pytest for AI agents", version="0.6.0")

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
    webhook_url: Optional[str] = None

class CaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    input: str
    expected_output: str
    match_type: str = "contains"

class DiagnoseRequest(BaseModel):
    input: str
    expected_output: str
    actual_output: str
    api_key: Optional[str] = None
    provider: Optional[str] = "gemini"

async def call_gemini(prompt: str, api_key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

async def semantic_match(expected: str, actual: str, api_key: str) -> dict:
    prompt = f"""You are evaluating an AI agent output.

Expected meaning: {expected}
Actual output: {actual}

Does the actual output convey the same meaning as expected, even if worded differently?
Reply in this exact JSON format with no extra text:
{{"match": true or false, "reason": "one sentence explanation"}}"""

    try:
        result = await call_gemini(prompt, api_key)
        cleaned = result.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except Exception as e:
        return {"match": False, "reason": str(e)}

async def diagnose_failure(input: str, expected: str, actual: str, api_key: str) -> str:
    prompt = f"""You are an expert AI agent debugger.

A test case failed. Analyze why and suggest a fix.

Input given to agent: {input}
Expected output: {expected}
Actual output: {actual}

Provide:
1. Why the agent likely failed
2. What the agent did wrong
3. A specific suggestion to fix it

Be concise and practical. Max 150 words."""

    try:
        return await call_gemini(prompt, api_key)
    except Exception as e:
        return f"Diagnosis unavailable: {str(e)}"

async def send_webhook(webhook_url: str, payload: dict):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(webhook_url, json=payload)
    except Exception:
        pass

@app.get("/")
def root():
    return {"name": "TestThread", "version": "0.6.0", "status": "running"}

@app.post("/suites")
def create_suite(suite: SuiteCreate):
    suite_id = str(uuid.uuid4())
    data = {
        "id": suite_id,
        "name": suite.name,
        "description": suite.description,
        "agent_endpoint": suite.agent_endpoint,
        "webhook_url": suite.webhook_url,
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
async def run_suite(suite_id: str, gemini_key: Optional[str] = None):
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

    active_key = gemini_key or GEMINI_API_KEY

    async with httpx.AsyncClient(timeout=30.0) as client:
        for case in cases:
            try:
                start_time = datetime.utcnow()
                response = await client.post(
                    suite["agent_endpoint"],
                    json={"input": case["input"]},
                    headers={"Content-Type": "application/json"}
                )
                end_time = datetime.utcnow()
                latency_ms = int((end_time - start_time).total_seconds() * 1000)
                actual = response.text
                expected = case["expected_output"]
                match_type = case.get("match_type", "contains")

                if match_type == "semantic" and active_key:
                    semantic = await semantic_match(expected, actual, active_key)
                    success = semantic["match"]
                    reason = None if success else semantic["reason"]
                elif match_type == "exact":
                    success = actual.strip() == expected.strip()
                    reason = None if success else f"Expected exact match: '{expected}'"
                elif match_type == "regex":
                    success = bool(re.search(expected, actual))
                    reason = None if success else f"Regex '{expected}' did not match"
                else:
                    success = expected.lower() in actual.lower()
                    reason = None if success else f"Expected '{expected}' not found in output"

                status = "passed" if success else "failed"

                diagnosis = None
                if not success and active_key:
                    diagnosis = await diagnose_failure(
                        case["input"], expected, actual, active_key
                    )

                pii_result = detect_pii(actual)
                if pii_result["detected"]:
                    status = "failed"
                    if not reason:
                        reason = f"PII detected in output: {', '.join(pii_result['types'])}"

            except Exception as e:
                status = "failed"
                actual = None
                reason = str(e)
                diagnosis = None
                latency_ms = None

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
                "diagnosis": diagnosis,
                "latency_ms": latency_ms if "latency_ms" in dir() else None,
                "pii_detected": pii_result["detected"] if "pii_result" in dir() else False,
                "pii_types": ", ".join(pii_result["types"]) if "pii_result" in dir() and pii_result["types"] else None,
            }
            supabase.table("test_results").insert(result_data).execute()
            results.append(result_data)

    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    avg_latency = int(sum(latencies) / len(latencies)) if latencies else None

    total = len(cases)
    curr_pass_rate = round((passed / total) * 100, 1) if total > 0 else 0

    prev_runs = supabase.table("test_runs")\
        .select("*")\
        .eq("suite_id", suite_id)\
        .eq("status", "completed")\
        .neq("id", run_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()

    regression = False
    prev_pass_rate = None

    if prev_runs.data:
        prev_run = prev_runs.data[0]
        prev_total = prev_run.get("total", 0)
        prev_passed = prev_run.get("passed", 0)
        prev_pass_rate = round((prev_passed / prev_total) * 100, 1) if prev_total > 0 else 0
        if curr_pass_rate < prev_pass_rate:
            regression = True

    supabase.table("test_runs").update({
        "status": "completed",
        "passed": passed,
        "failed": failed,
        "completed_at": datetime.utcnow().isoformat(),
        "avg_latency_ms": avg_latency,
        "regression": regression,
        "prev_pass_rate": prev_pass_rate,
        "curr_pass_rate": curr_pass_rate,
    }).eq("id", run_id).execute()

    final = {
        "run_id": run_id,
        "total": total,
        "passed": passed,
        "failed": failed,
        "status": "completed",
        "avg_latency_ms": avg_latency,
        "curr_pass_rate": curr_pass_rate,
        "prev_pass_rate": prev_pass_rate,
        "regression": regression,
        "regression_message": f"⚠️ Regression detected. Pass rate dropped from {prev_pass_rate}% to {curr_pass_rate}%" if regression else None,
        "results": results
    }

    webhook_url = suite.get("webhook_url")
    if webhook_url and (failed > 0 or regression):
        await send_webhook(webhook_url, {
            "event": "test_run_completed",
            "suite": suite["name"],
            "run_id": run_id,
            "passed": passed,
            "failed": failed,
            "total": total,
            "regression": regression,
            "curr_pass_rate": curr_pass_rate,
            "prev_pass_rate": prev_pass_rate,
        })

    return final

@app.post("/trigger")
async def trigger_run(suite_id: str, gemini_key: Optional[str] = None):
    return await run_suite(suite_id, gemini_key)

@app.post("/diagnose")
async def diagnose(req: DiagnoseRequest):
    active_key = req.api_key or GEMINI_API_KEY
    if not active_key:
        raise HTTPException(status_code=400, detail="No API key provided")
    result = await diagnose_failure(req.input, req.expected_output, req.actual_output, active_key)
    return {"diagnosis": result}

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