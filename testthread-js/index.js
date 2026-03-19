const https = require("https");
const http = require("http");

class TestThread {
  constructor(baseUrl = "https://test-thread-production.up.railway.app", geminiKey = null) {
    this.base = baseUrl.replace(/\/$/, "");
    this.geminiKey = geminiKey;
  }

  _request(method, path, body = null) {
    return new Promise((resolve, reject) => {
      const url = new URL(this.base + path);
      const lib = url.protocol === "https:" ? https : http;
      const options = {
        hostname: url.hostname,
        path: url.pathname + url.search,
        method,
        headers: { "Content-Type": "application/json" },
      };
      const req = lib.request(options, (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => resolve(JSON.parse(data)));
      });
      req.on("error", reject);
      if (body) req.write(JSON.stringify(body));
      req.end();
    });
  }

  createSuite(name, agentEndpoint, description = null, webhookUrl = null) {
    return this._request("POST", "/suites", {
      name,
      description,
      agent_endpoint: agentEndpoint,
      webhook_url: webhookUrl,
    });
  }

  addCase(suiteId, name, input, expectedOutput, matchType = "contains", description = null) {
    return this._request("POST", `/suites/${suiteId}/cases`, {
      name,
      description,
      input,
      expected_output: expectedOutput,
      match_type: matchType,
    });
  }

  runSuite(suiteId) {
    const query = this.geminiKey ? `?gemini_key=${this.geminiKey}` : "";
    return this._request("POST", `/suites/${suiteId}/run${query}`);
  }

  diagnose(input, expectedOutput, actualOutput) {
    return this._request("POST", "/diagnose", {
      input,
      expected_output: expectedOutput,
      actual_output: actualOutput,
      api_key: this.geminiKey,
    });
  }

  getRun(runId) {
    return this._request("GET", `/runs/${runId}`);
  }

  listSuites() {
    return this._request("GET", "/suites");
  }

  listRuns() {
    return this._request("GET", "/runs");
  }

  stats() {
    return this._request("GET", "/dashboard/stats");
  }
}

module.exports = TestThread;