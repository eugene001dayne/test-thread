# TestThread 🧵

**pytest for AI agents.**

The open-source testing framework that tells you if your AI agent is actually working — or quietly breaking.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![API](https://img.shields.io/badge/API-live-brightgreen)](https://test-thread-production.up.railway.app)
[![Dashboard](https://img.shields.io/badge/Dashboard-live-brightgreen)](https://test-thread.lovable.app)
[![PyPI](https://img.shields.io/badge/PyPI-testthread-blue)](https://pypi.org/project/testthread/)
[![npm](https://img.shields.io/badge/npm-testthread-red)](https://www.npmjs.com/package/testthread)
[![Version](https://img.shields.io/badge/version-0.10.0-green)](https://github.com/eugene001dayne/test-thread/releases)

---

## The Problem

You build an AI agent. It works in testing. You ship it.

Then it starts hallucinating. Returning wrong formats. Calling the wrong tools. Breaking your pipeline.

You find out when something downstream crashes — not before.

**TestThread fixes that.**

---

## What TestThread Does

Define what your agent *should* do. TestThread runs it, checks the output, and tells you exactly what passed and what failed — with AI diagnosis explaining why.

---

## Features

| Feature | Description |
|---------|-------------|
| ✅ **Test Suites** | Group test cases per agent |
| ✅ **4 Match Types** | contains, exact, regex, semantic (AI-powered) |
| 🧠 **AI Diagnosis** | When a test fails, AI explains why and suggests a fix |
| 📉 **Regression Detection** | Flags when pass rate drops vs previous run |
| 🔒 **PII Detection** | Auto-fails if agent leaks emails, keys, SSNs, credit cards |
| ⚡ **Latency Tracking** | Response time per test, average per run |
| 💰 **Cost Estimation** | Estimated token cost per run |
| 🛤️ **Trajectory Assertions** | Test agent steps, not just output |
| ⏰ **Scheduled Runs** | Run suites hourly, daily, or weekly automatically |
| ⚙️ **CI/CD Integration** | GitHub Action runs tests on every push |
| 🔔 **Webhook Alerts** | Get notified when tests fail or regress |
| 📁 **CSV Import** | Bulk import test cases from a spreadsheet |
| 🛡️ **Rate Limiting** | API protected from abuse |

---

## Quick Start
```bash
pip install testthread
```
```python
from testthread import TestThread

tt = TestThread(gemini_key="your-gemini-key")

# Create a test suite
suite = tt.create_suite(
    name="My Agent Tests",
    agent_endpoint="https://your-agent.com/run"
)

# Add test cases
tt.add_case(
    suite_id=suite["id"],
    name="Basic response check",
    input="What is 2 + 2?",
    expected_output="4",
    match_type="contains"
)

tt.add_case(
    suite_id=suite["id"],
    name="Semantic check",
    input="Say hello",
    expected_output="a friendly greeting",
    match_type="semantic"
)

# Run the suite
result = tt.run_suite(suite["id"])
print(f"Passed: {result['passed']} | Failed: {result['failed']}")
print(f"Pass Rate: {result['curr_pass_rate']}%")
print(f"Estimated Cost: ${result['estimated_cost_usd']}")
```

---

## JavaScript
```bash
npm install testthread
```
```javascript
const TestThread = require("testthread");

const tt = new TestThread("https://test-thread-production.up.railway.app", "your-gemini-key");

const suite = await tt.createSuite("My Agent", "https://your-agent.com/run");
await tt.addCase(suite.id, "Hello test", "Say hi", "hello", "contains");
const result = await tt.runSuite(suite.id);
console.log(`Passed: ${result.passed} | Failed: ${result.failed}`);
```

---

## Match Types

| Type | Description |
|------|-------------|
| `contains` | Output contains the expected string |
| `exact` | Output matches exactly |
| `regex` | Output matches a regex pattern |
| `semantic` | AI judges if meaning matches (requires Gemini key) |

---

## Trajectory Assertions

Test not just *what* your agent returned, but *how* it got there.
```python
import requests

# Set assertions on a test case
requests.post(f"{BASE}/suites/{suite_id}/cases/{case_id}/assertions", json=[
    {"type": "tool_called", "value": "search"},
    {"type": "tool_not_called", "value": "delete_user"},
    {"type": "max_steps", "value": 5}
])

# After your agent runs, submit its trajectory
requests.post(f"{BASE}/trajectory", json={
    "run_id": run_id,
    "case_id": case_id,
    "steps": [
        {"tool": "search", "input": "query", "output": "results", "order": 1},
        {"tool": "summarize", "input": "results", "output": "summary", "order": 2}
    ]
})
```

**Supported assertion types:**
- `tool_called` — assert a tool was used
- `tool_not_called` — assert a tool was NOT used
- `max_steps` — assert agent completed in N steps or fewer
- `min_steps` — assert agent took at least N steps
- `tool_order` — assert tools were called in a specific order
- `action_called` — assert a specific action was performed

---

## CI/CD Integration

Add one file to your repo and TestThread runs on every push:

1. Add your suite ID to GitHub Secrets as `TESTTHREAD_SUITE_ID`
2. Copy `.github/workflows/testthread.yml` from this repo into your project

Every push to main now runs your agent tests automatically. Fails the build if tests regress.

---

## Scheduled Runs
```python
import requests

requests.post(f"{BASE}/suites/{suite_id}/schedule", json={
    "schedule": "daily",
    "schedule_enabled": True
})
```

Options: `hourly`, `daily`, `weekly`

---

## Live Dashboard

View all your test results at **[test-thread.lovable.app](https://test-thread.lovable.app)**

---

## API Reference

Full docs at **[test-thread-production.up.railway.app/docs](https://test-thread-production.up.railway.app/docs)**

---

## Self-Host
```bash
git clone https://github.com/eugene001dayne/test-thread.git
cd test-thread
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## Part of the Thread Suite

TestThread is part of a suite of open-source reliability tools for AI agents.

| Tool | What it does |
|------|-------------|
| [Iron-Thread](https://github.com/eugene001dayne/iron-thread) | Validates AI output structure before it hits your database |
| **TestThread** | Tests whether your agent behaves correctly across runs |
| PromptThread *(coming soon)* | Versions and tracks prompt performance over time |

---

## License

Apache 2.0 — free to use, modify, and distribute.

---

Built for developers who ship AI agents and need to know they work.
