"use strict";

const fetch = require("node-fetch");

class TestThread {
  constructor(
    baseUrl = "https://test-thread.onrender.com",
    geminiKey = null
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.geminiKey = geminiKey;
  }

  async _request(method, path, body = null) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${this.baseUrl}${path}`, opts);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`TestThread error ${res.status}: ${text}`);
    }
    return res.json();
  }

  // ── Suites ─────────────────────────────────────────────────────────────────

  createSuite(name, agentEndpoint, description = null, webhookUrl = null) {
    return this._request("POST", "/suites", {
      name,
      agent_endpoint: agentEndpoint,
      description,
      webhook_url: webhookUrl,
    });
  }

  listSuites() {
    return this._request("GET", "/suites");
  }

  // ── Cases ──────────────────────────────────────────────────────────────────

  addCase(suiteId, name, input, expectedOutput, matchType = "contains", description = null, source = "manual") {
    return this._request("POST", `/suites/${suiteId}/cases`, {
      name,
      input,
      expected_output: expectedOutput,
      match_type: matchType,
      description,
      source,
    });
  }

  listCases(suiteId) {
    return this._request("GET", `/suites/${suiteId}/cases`);
  }

  // ── Run ────────────────────────────────────────────────────────────────────

  runSuite(suiteId) {
    return this._request("POST", `/suites/${suiteId}/run`, {
      gemini_key: this.geminiKey,
    });
  }

  // ── Adversarial generation (v0.11.0) ────────────────────────────────────

  generateAdversarial(suiteId, count = 5, focus = "edge_cases") {
    return this._request("POST", `/suites/${suiteId}/generate-adversarial`, {
      count,
      focus,
    });
  }

  // ── Production monitoring (v0.12.0) ─────────────────────────────────────

  monitor(suiteId, input, actualOutput) {
    return this._request("POST", "/monitor", {
      suite_id: suiteId,
      input,
      actual_output: actualOutput,
    });
  }

  getDrift(suiteId) {
    return this._request("GET", `/monitor/${suiteId}/drift`);
  }

  // ── Schedule ───────────────────────────────────────────────────────────────

  setSchedule(suiteId, schedule, enabled = true) {
    return this._request("POST", `/suites/${suiteId}/schedule`, {
      schedule,
      schedule_enabled: enabled,
    });
  }

  getSchedule(suiteId) {
    return this._request("GET", `/suites/${suiteId}/schedule`);
  }

  // ── Diagnose ───────────────────────────────────────────────────────────────

  diagnose(input, expectedOutput, actualOutput) {
    return this._request("POST", "/diagnose", {
      input,
      expected_output: expectedOutput,
      actual_output: actualOutput,
    });
  }

  // ── Runs ───────────────────────────────────────────────────────────────────

  getRun(runId) {
    return this._request("GET", `/runs/${runId}`);
  }

  listRuns() {
    return this._request("GET", "/runs");
  }

  // ── Stats ──────────────────────────────────────────────────────────────────

  stats() {
    return this._request("GET", "/dashboard/stats");
  }

  health() {
    return this._request("GET", "/");
  }
}

module.exports = TestThread;