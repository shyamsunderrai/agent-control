import { type Page,test as base } from "@playwright/test";

import type {
  AgentControlsResponse,
  AgentSummary,
  Control,
  EvaluatorsResponse,
  GetAgentResponse,
  ListAgentsResponse,
} from "@/core/api/types";

/**
 * Mock data for API responses
 * Uses API types to ensure type safety - if backend changes, TypeScript will catch it
 */

// Satisfies ensures type checking while allowing inference of literal types
const agentsList: AgentSummary[] = [
  {
    agent_id: "agent-1",
    agent_name: "Customer Support Bot",
    policy_id: 1,
    created_at: "2024-01-01T00:00:00Z",
    step_count: 5,
    evaluator_count: 2,
    active_controls_count: 3,
  },
  {
    agent_id: "agent-2",
    agent_name: "Data Analysis Agent",
    policy_id: 2,
    created_at: "2024-01-02T00:00:00Z",
    step_count: 3,
    evaluator_count: 1,
    active_controls_count: 2,
  },
  {
    agent_id: "agent-3",
    agent_name: "Code Review Assistant",
    policy_id: 3,
    created_at: "2024-01-03T00:00:00Z",
    step_count: 8,
    evaluator_count: 4,
    active_controls_count: 5,
  },
];

const agentsResponse: ListAgentsResponse = {
  agents: agentsList,
  pagination: {
    total: 3,
    limit: 25,
    has_more: false,
    next_cursor: null,
  },
};

const agentResponse: GetAgentResponse = {
  agent: {
    agent_id: "agent-1",
    agent_name: "Customer Support Bot",
    agent_description: "Handles customer inquiries and support tickets",
    agent_created_at: "2024-01-01T00:00:00Z",
    agent_updated_at: "2024-01-15T00:00:00Z",
    agent_version: "1.0.0",
    agent_metadata: null,
  },
  steps: [],
  evaluators: [],
};

const controlsList: Control[] = [
  {
    id: 1,
    name: "PII Detection",
    control: {
      description: "Detects and masks personally identifiable information",
      enabled: true,
      execution: "server",
      scope: { step_types: ["llm"], stages: ["post"] },
      selector: { path: "output" },
      evaluator: {
        name: "regex",
        config: { pattern: "\\b\\d{3}-\\d{2}-\\d{4}\\b" },
      },
      action: { decision: "deny" },
      tags: ["pii", "compliance"],
    },
  },
  {
    id: 2,
    name: "SQL Injection Guard",
    control: {
      description: "Prevents SQL injection attacks",
      enabled: true,
      execution: "server",
      scope: {
        step_types: ["tool"],
        step_names: ["database_query"],
        step_name_regex: "^db_.*",
        stages: ["pre"],
      },
      selector: { path: "input.query" },
      evaluator: {
        name: "sql",
        config: { mode: "safe" },
      },
      action: { decision: "deny" },
      tags: ["security"],
    },
  },
  {
    id: 3,
    name: "Rate Limiter",
    control: {
      description: "Limits API call frequency",
      enabled: false,
      execution: "server",
      scope: { step_types: ["llm"], stages: ["pre"] },
      selector: { path: "*" },
      evaluator: {
        name: "list",
        config: { values: [], logic: "any", match_on: "match" },
      },
      action: { decision: "allow" },
      tags: [],
    },
  },
];

const controlsResponse: AgentControlsResponse = {
  controls: controlsList,
};

const evaluatorsResponse: EvaluatorsResponse = {
  regex: {
    name: "Regex",
    version: "1.0.0",
    description: "Pattern matching using regular expressions",
    requires_api_key: false,
    timeout_ms: 5000,
    config_schema: {
      type: "object",
      properties: {
        pattern: { type: "string", description: "Regular expression pattern" },
      },
      required: ["pattern"],
    },
  },
  list: {
    name: "List",
    version: "1.0.0",
    description: "Match against a list of allowed or blocked values",
    requires_api_key: false,
    timeout_ms: 5000,
    config_schema: {
      type: "object",
      properties: {
        values: { type: "array", items: { type: "string" } },
        logic: { type: "string", enum: ["any", "all"] },
        match_on: { type: "string", enum: ["match", "no_match"] },
      },
      required: ["values"],
    },
  },
  sql: {
    name: "SQL",
    version: "1.0.0",
    description: "SQL injection detection and prevention",
    requires_api_key: false,
    timeout_ms: 5000,
    config_schema: {
      type: "object",
      properties: {
        mode: { type: "string", enum: ["safe", "strict"] },
      },
    },
  },
  json: {
    name: "JSON",
    version: "1.0.0",
    description: "JSON schema validation",
    requires_api_key: false,
    timeout_ms: 5000,
    config_schema: {
      type: "object",
      properties: {
        schema: { type: "object" },
      },
      required: ["schema"],
    },
  },
  "galileo-luna2": {
    name: "Galileo Luna-2",
    version: "1.0.0",
    description: "AI-powered content moderation using Galileo Luna-2",
    requires_api_key: true,
    timeout_ms: 30000,
    config_schema: {
      type: "object",
      properties: {
        threshold: { type: "number" },
      },
    },
  },
};

/**
 * Typed mock data for tests
 */
export const mockData = {
  agents: agentsResponse,
  agent: agentResponse,
  controls: controlsResponse,
  evaluators: evaluatorsResponse,
} as const;

/**
 * Helper to set up API route mocking
 */
export async function mockApiRoutes(page: Page) {
  // Mock agents list
  await page.route("**/api/v1/agents?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockData.agents),
    });
  });

  // Mock agent controls - must be registered before single agent route
  await page.route("**/api/v1/agents/*/controls", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockData.controls),
    });
  });

  // Mock single agent
  await page.route("**/api/v1/agents/*", async (route, request) => {
    const url = request.url();

    // Skip if it's a controls request (handled by separate route above)
    if (url.includes("/controls")) {
      await route.continue();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockData.agent),
    });
  });

  // Mock evaluators list
  await page.route("**/api/v1/evaluators", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockData.evaluators),
    });
  });

  // Mock control creation
  await page.route("**/api/v1/controls", async (route, request) => {
    if (request.method() === "PUT") {
      const body = await request.postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          control_id: 100,
          name: body.name || "New Control",
        }),
      });
      return;
    }
    await route.continue();
  });

  // Mock control update
  await page.route("**/api/v1/controls/*/data", async (route, request) => {
    if (request.method() === "PUT") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
        }),
      });
      return;
    }
    await route.continue();
  });
}

/**
 * Extended test with mocked API
 */
export const test = base.extend<{ mockedPage: Page }>({
  /* eslint-disable react-hooks/rules-of-hooks */
  mockedPage: async ({ page }, use) => {
    await mockApiRoutes(page);
    await use(page);
  },
  /* eslint-enable react-hooks/rules-of-hooks */
});

export { expect } from "@playwright/test";
