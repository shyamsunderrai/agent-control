"""
Agent Control Demo - Policy Setup
===================================
Creates all controls and policies for the MAS AIRG demo.
Run this ONCE after agent-control server is healthy and all agents have registered.

Usage:
    python setup_policies.py [--server http://localhost:8000] [--api-key KEY]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

import httpx


# ── HTTP helpers ──────────────────────────────────────────────────────────────

class PolicyClient:
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    async def create_control(self, name: str, data: dict[str, Any]) -> int:
        """Create control, skip if already exists. Returns control ID."""
        resp = await self.client.put(
            "/api/v1/controls",
            json={"name": name, "data": data},
        )
        if resp.status_code == 409:
            # Already exists - fetch its ID
            list_resp = await self.client.get("/api/v1/controls", params={"name": name, "limit": 5})
            list_resp.raise_for_status()
            controls = list_resp.json().get("controls", [])
            existing = next((c for c in controls if c["name"] == name), None)
            if existing:
                print(f"  ↩  control '{name}' already exists (id={existing['id']})")
                return existing["id"]
            raise RuntimeError(f"Control '{name}' exists but not found in list")
        resp.raise_for_status()
        ctrl_id = resp.json()["control_id"]
        print(f"  ✓  created control '{name}' (id={ctrl_id})")
        return ctrl_id

    async def create_policy(self, name: str) -> int:
        """Create policy. Returns policy ID."""
        resp = await self.client.put("/api/v1/policies", json={"name": name})
        if resp.status_code == 409:
            # Policy exists but may not be fully configured — find its ID by scanning
            pid = 1
            while True:
                check = await self.client.get(f"/api/v1/policies/{pid}/controls")
                if check.status_code == 404:
                    pid -= 1
                    break
                pid += 1
            if pid < 1:
                raise RuntimeError(f"Policy '{name}' exists but ID could not be found")
            print(f"  ↩  policy '{name}' already exists (id={pid}), continuing setup")
            return pid
        resp.raise_for_status()
        policy_id = resp.json()["policy_id"]
        print(f"  ✓  created policy '{name}' (id={policy_id})")
        return policy_id

    async def agent_has_policies(self, agent_name: str) -> bool:
        """Check if agent already has policies assigned."""
        resp = await self.client.get(f"/api/v1/agents/{agent_name}/policies")
        if resp.status_code == 200:
            policies = resp.json().get("policy_ids", [])
            return len(policies) > 0
        return False

    async def add_control_to_policy(self, policy_id: int, control_id: int) -> None:
        resp = await self.client.post(f"/api/v1/policies/{policy_id}/controls/{control_id}")
        if resp.status_code != 409:
            resp.raise_for_status()

    async def assign_policy_to_agent(self, agent_name: str, policy_id: int) -> None:
        resp = await self.client.post(f"/api/v1/agents/{agent_name}/policies/{policy_id}")
        if resp.status_code != 409:
            resp.raise_for_status()

    async def wait_for_agent(self, agent_name: str, max_attempts: int = 20) -> bool:
        for attempt in range(max_attempts):
            resp = await self.client.get(f"/api/v1/agents/{agent_name}")
            if resp.status_code == 200:
                return True
            await asyncio.sleep(3)
            print(f"  ⏳ waiting for agent '{agent_name}' ({attempt+1}/{max_attempts})...")
        return False


# ── Control definitions ───────────────────────────────────────────────────────

def _server_control(
    scope: dict[str, Any],
    condition: dict[str, Any],
    action: dict[str, Any],
    description: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    ctrl: dict[str, Any] = {
        "execution": "server",
        "scope": scope,
        "condition": condition,
        "action": action,
    }
    if description:
        ctrl["description"] = description
    if tags:
        ctrl["tags"] = tags
    return ctrl


# ─ Loan Underwriting Controls ────────────────────────────────────────────────

LOAN_CONTROLS = [
    (
        "loan-fairness-block-protected-attributes",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["pre"]},
            condition={
                "selector": {"path": "input"},
                "evaluator": {
                    "name": "regex",
                    "config": {
                        # Detects prompts instructing the agent to use protected attributes
                        "pattern": r"(?i)\b(age|gender|race|ethnicity|religion|marital.status|national.origin|disability|sexual.orientation)\b.{0,60}\b(factor|consider|weight|use|include|based|assess|account|reflect)\b"
                    },
                },
            },
            action={"decision": "deny"},
            description="MAS AIRG 4.3: Block credit decisions using protected attributes",
            tags=["fairness", "bias-prevention", "mas-airg-4.3"],
        ),
    ),
    (
        "loan-transparency-require-explanation",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["post"]},
            condition={
                "not": {
                    "selector": {"path": "output"},
                    "evaluator": {
                        "name": "regex",
                        "config": {
                            "pattern": r"(?i)(reason|because|based on|due to|criteria|factor|metric|score|ratio|income|employment|history)"
                        },
                    },
                }
            },
            action={
                "decision": "steer",
                "steering_context": {
                    "message": (
                        "Decision lacks required explanation. Provide reasoning based solely "
                        "on financial criteria (credit score, income, DTI ratio, employment "
                        "history). Do NOT reference age, gender, race, or other protected attributes."
                    )
                },
            },
            description="MAS AIRG 4.4: Require explainable reasoning in credit decisions",
            tags=["transparency", "explainability", "mas-airg-4.4"],
        ),
    ),
    (
        "loan-audit-all-decisions",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["post"]},
            condition={
                "selector": {"path": "output"},
                "evaluator": {
                    "name": "regex",
                    "config": {
                        "pattern": r"(?i)\b(approve|deny|reject|decline|recommend|decision|assessment)\b"
                    },
                },
            },
            action={"decision": "observe"},
            description="MAS AIRG 4.8: Mandatory audit log of all credit decisions",
            tags=["audit", "compliance", "mas-airg-4.8"],
        ),
    ),
]

# ─ Customer Support Controls ─────────────────────────────────────────────────

CUSTOMER_CONTROLS = [
    (
        "customer-security-block-prompt-injection",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["pre"]},
            condition={
                "selector": {"path": "input"},
                "evaluator": {
                    "name": "regex",
                    "config": {
                        "pattern": r"(?i)(ignore.{0,20}(previous|prior|above|all).{0,20}(instruction|rule|guideline)|forget.{0,20}instruction|you.are.now|new.persona|act.as.if|pretend.you|disregard.{0,20}all|jailbreak|DAN.mode|developer.mode|bypass.safety|override.system)"
                    },
                },
            },
            action={"decision": "deny"},
            description="MAS AIRG 4.7: Block prompt injection and adversarial inputs",
            tags=["security", "prompt-injection", "mas-airg-4.7"],
        ),
    ),
    (
        "customer-privacy-block-pii-output",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["post"]},
            condition={
                "or": [
                    {
                        "selector": {"path": "output"},
                        "evaluator": {
                            "name": "regex",
                            "config": {"pattern": r"[STFG]\d{7}[A-Z]"},  # Singapore NRIC
                        },
                    },
                    {
                        "selector": {"path": "output"},
                        "evaluator": {
                            "name": "regex",
                            "config": {"pattern": r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"},  # Credit card
                        },
                    },
                    {
                        "selector": {"path": "output"},
                        "evaluator": {
                            "name": "regex",
                            "config": {"pattern": r"\b\d{3}-\d{2}-\d{4}\b"},  # SSN
                        },
                    },
                ]
            },
            action={"decision": "deny"},
            description="MAS AIRG 4.2: Prevent PII (NRIC, credit card, SSN) in agent outputs",
            tags=["pii", "data-protection", "mas-airg-4.2"],
        ),
    ),
    (
        "customer-access-control-sensitive-ops",
        _server_control(
            scope={"step_types": ["tool"], "step_names": ["account_action"], "stages": ["pre"]},
            condition={
                "selector": {"path": "input"},
                "evaluator": {
                    "name": "list",
                    "config": {
                        "values": [
                            "transfer_funds",
                            "change_password",
                            "close_account",
                            "override_limit",
                            "reset_pin",
                            "add_payee",
                        ],
                        "match_mode": "contains",
                        "case_sensitive": False,
                    },
                },
            },
            action={
                "decision": "steer",
                "steering_context": {
                    "message": (
                        "High-risk account operation detected. Before proceeding: "
                        "1) Verify customer identity via OTP or biometric, "
                        "2) Log the authentication event, "
                        "3) Confirm customer intent. Only retry after verification."
                    )
                },
            },
            description="MAS AIRG 4.1: Enforce authentication for sensitive account operations",
            tags=["access-control", "authentication", "mas-airg-4.1"],
        ),
    ),
]

# ─ Trade Execution Controls ───────────────────────────────────────────────────

TRADE_CONTROLS = [
    (
        "trade-human-oversight-large-amount",
        _server_control(
            scope={"step_types": ["tool"], "step_names": ["execute_trade"], "stages": ["pre"]},
            condition={
                "selector": {"path": "input"},
                "evaluator": {
                    "name": "json",
                    "config": {
                        "field_constraints": {
                            "amount": {"type": "number", "min": 1000000}
                        },
                        "allow_invalid_json": True,
                    },
                },
            },
            action={
                "decision": "steer",
                "steering_context": {
                    "message": (
                        "Trade value exceeds $1M oversight threshold. "
                        "PAUSE execution and: "
                        "1) Submit trade details to compliance officer for approval, "
                        "2) Record approval reference number, "
                        "3) Only execute after receiving explicit written approval. "
                        "Do NOT execute without human authorization."
                    )
                },
            },
            description="MAS AIRG 4.5: Human approval required for trades exceeding $1M",
            tags=["human-oversight", "large-trade", "mas-airg-4.5"],
        ),
    ),
    (
        "trade-security-block-sql-injection",
        _server_control(
            scope={"step_types": ["tool"], "step_names": ["query_market_data"], "stages": ["pre"]},
            condition={
                "selector": {"path": "input"},
                "evaluator": {
                    "name": "sql",
                    "config": {
                        "blocked_operations": [
                            "DROP", "DELETE", "INSERT", "UPDATE",
                            "CREATE", "ALTER", "EXEC", "EXECUTE",
                            "UNION", "TRUNCATE",
                        ],
                        "require_limit": False,
                    },
                },
            },
            action={"decision": "deny"},
            description="MAS AIRG 4.7: Block SQL injection in market data queries",
            tags=["sql-injection", "cybersecurity", "mas-airg-4.7"],
        ),
    ),
    (
        "trade-integrity-block-insider-language",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["post"]},
            condition={
                "selector": {"path": "output"},
                "evaluator": {
                    "name": "list",
                    "config": {
                        "values": [
                            "insider information",
                            "insider info",
                            "non-public",
                            "material non-public",
                            "confidential source",
                            "before the announcement",
                            "tip from",
                            "heard from someone",
                            "not yet public",
                            "advance knowledge",
                        ],
                        "match_mode": "contains",
                        "case_sensitive": False,
                    },
                },
            },
            action={"decision": "deny"},
            description="MAS AIRG 4.3: Block recommendations referencing insider information",
            tags=["market-integrity", "insider-trading", "mas-airg-4.3"],
        ),
    ),
    (
        "trade-audit-all-recommendations",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["post"]},
            condition={
                "selector": {"path": "output"},
                "evaluator": {
                    "name": "regex",
                    "config": {
                        "pattern": r"(?i)\b(buy|sell|hold|execute|trade|position|recommend|suggest)\b"
                    },
                },
            },
            action={"decision": "observe"},
            description="MAS AIRG 4.8: Audit log all trade recommendations",
            tags=["audit", "trade-log", "mas-airg-4.8"],
        ),
    ),
]

# ─ AML Compliance Controls ────────────────────────────────────────────────────

AML_CONTROLS = [
    (
        "aml-block-sanctioned-entity-clearance",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["post"]},
            condition={
                "and": [
                    {
                        "selector": {"path": "output"},
                        "evaluator": {
                            "name": "list",
                            "config": {
                                "values": [
                                    "clear",
                                    "approve",
                                    "whitelist",
                                    "false positive",
                                    "no issue",
                                    "pass",
                                    "not a match",
                                ],
                                "match_mode": "contains",
                                "case_sensitive": False,
                            },
                        },
                    },
                    {
                        "selector": {"path": "input"},
                        "evaluator": {
                            "name": "list",
                            "config": {
                                "values": [
                                    "OFAC",
                                    "SDN list",
                                    "sanctioned",
                                    "sanctions",
                                    "PEP",
                                    "watchlist",
                                    "blacklist",
                                    "UN list",
                                    "MAS list",
                                ],
                                "match_mode": "contains",
                                "case_sensitive": False,
                            },
                        },
                    },
                ]
            },
            action={"decision": "deny"},
            description="MAS AIRG 4.6: Prevent auto-clearance of sanctioned entity matches",
            tags=["aml", "sanctions", "mas-airg-4.6"],
        ),
    ),
    (
        "aml-escalate-low-confidence",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["post"]},
            condition={
                "selector": {"path": "output"},
                "evaluator": {
                    "name": "regex",
                    "config": {
                        "pattern": r"(?i)\b(uncertain|not sure|possibly|may be|might be|unclear|low confidence|limited information|unsure|ambiguous|inconclusive)\b"
                    },
                },
            },
            action={
                "decision": "steer",
                "steering_context": {
                    "message": (
                        "Low-confidence AML screening result detected. "
                        "This case requires human review. Steps: "
                        "1) Escalate to senior compliance analyst immediately, "
                        "2) Do NOT auto-clear or auto-flag without human review, "
                        "3) Document the escalation reason, "
                        "4) Await analyst decision before proceeding."
                    )
                },
            },
            description="MAS AIRG 4.5: Force human escalation on uncertain AML determinations",
            tags=["human-oversight", "escalation", "mas-airg-4.5"],
        ),
    ),
    (
        "aml-audit-all-screening-decisions",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["post"]},
            condition={
                "selector": {"path": "output"},
                "evaluator": {
                    "name": "regex",
                    "config": {
                        "pattern": r"(?i)\b(screen|check|match|flag|alert|suspicious|clear|approve|reject|escalate|risk)\b"
                    },
                },
            },
            action={"decision": "observe"},
            description="MAS AIRG 4.8: Mandatory audit trail for all AML screening decisions",
            tags=["audit", "aml-trail", "mas-airg-4.8"],
        ),
    ),
]

# ─ Report Generation Controls ────────────────────────────────────────────────

REPORT_CONTROLS = [
    (
        "report-security-block-dangerous-code",
        _server_control(
            scope={"step_types": ["tool"], "step_names": ["execute_code"], "stages": ["pre"]},
            condition={
                "selector": {"path": "input"},
                "evaluator": {
                    "name": "list",
                    "config": {
                        "values": [
                            "os.system",
                            "subprocess",
                            "exec(",
                            "eval(",
                            "shutil.rmtree",
                            "os.remove",
                            "os.unlink",
                            "__import__",
                            "open('/etc",
                            "open('/root",
                            "open('/proc",
                            "rm -rf",
                        ],
                        "match_mode": "contains",
                        "case_sensitive": False,
                    },
                },
            },
            action={"decision": "deny"},
            description="MAS AIRG 4.7: Block OS/filesystem operations in generated code",
            tags=["code-safety", "cybersecurity", "mas-airg-4.7"],
        ),
    ),
    (
        "report-security-block-destructive-sql",
        _server_control(
            scope={"step_types": ["tool"], "step_names": ["run_sql_query"], "stages": ["pre"]},
            condition={
                "selector": {"path": "input"},
                "evaluator": {
                    "name": "sql",
                    "config": {
                        "blocked_operations": [
                            "DROP",
                            "DELETE",
                            "TRUNCATE",
                            "UPDATE",
                            "ALTER",
                            "CREATE",
                            "INSERT",
                        ],
                        "require_limit": False,
                    },
                },
            },
            action={"decision": "deny"},
            description="MAS AIRG 4.7: Block destructive SQL in report data queries",
            tags=["sql-safety", "data-integrity", "mas-airg-4.7"],
        ),
    ),
    (
        "report-security-block-credential-exposure",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["post"]},
            condition={
                "selector": {"path": "output"},
                "evaluator": {
                    "name": "regex",
                    "config": {
                        "pattern": r"(?i)(password|secret|api.?key|token|credential|passwd|private.key)['\"\s]*[:=]['\"\s]*\S{6,}"
                    },
                },
            },
            action={"decision": "deny"},
            description="MAS AIRG 4.7: Prevent hardcoded credentials in report output",
            tags=["secret-detection", "security", "mas-airg-4.7"],
        ),
    ),
    (
        "report-quality-flag-placeholder-data",
        _server_control(
            scope={"step_types": ["llm"], "stages": ["post"]},
            condition={
                "selector": {"path": "output"},
                "evaluator": {
                    "name": "list",
                    "config": {
                        "values": [
                            "[TODO",
                            "[PLACEHOLDER",
                            "INSERT_VALUE",
                            "TBD",
                            "FIXME",
                            "XXX",
                            "SAMPLE_DATA",
                            "[insert",
                            "[add actual",
                        ],
                        "match_mode": "contains",
                        "case_sensitive": False,
                    },
                },
            },
            action={
                "decision": "steer",
                "steering_context": {
                    "message": (
                        "Report contains placeholder data. Before submission: "
                        "Replace ALL placeholder values ([TODO], [PLACEHOLDER], TBD, etc.) "
                        "with actual figures from the data source. "
                        "Regulatory reports must contain verified data only."
                    )
                },
            },
            description="MAS AIRG 4.2: Flag incomplete placeholder data in regulatory reports",
            tags=["data-quality", "accuracy", "mas-airg-4.2"],
        ),
    ),
]


# ── Agent-to-controls mapping ─────────────────────────────────────────────────

AGENT_POLICIES = {
    "loan-underwriting-agent": ("loan-underwriting-policy", LOAN_CONTROLS),
    "customer-support-agent": ("customer-support-policy", CUSTOMER_CONTROLS),
    "trade-execution-agent": ("trade-execution-policy", TRADE_CONTROLS),
    "aml-compliance-agent": ("aml-compliance-policy", AML_CONTROLS),
    "report-generation-agent": ("report-generation-policy", REPORT_CONTROLS),
}


# ── Main setup ────────────────────────────────────────────────────────────────

async def setup(server_url: str, api_key: str | None) -> None:
    print(f"\n{'='*60}")
    print(f"  Agent Control Demo - Policy Setup")
    print(f"  Server: {server_url}")
    print(f"{'='*60}\n")

    async with PolicyClient(server_url, api_key) as client:
        # Verify server is healthy
        try:
            resp = await client.client.get("/health")
            resp.raise_for_status()
            print(f"✓ Server healthy: {server_url}\n")
        except Exception as e:
            print(f"✗ Server not available: {e}")
            sys.exit(1)

        for agent_name, (policy_name, controls) in AGENT_POLICIES.items():
            print(f"\n{'─'*50}")
            print(f"  Agent: {agent_name}")
            print(f"{'─'*50}")

            # Wait for agent to register itself
            print(f"  Waiting for agent registration...")
            registered = await client.wait_for_agent(agent_name)
            if not registered:
                print(f"  ⚠  Agent '{agent_name}' not found after waiting. Skipping.")
                print(f"     Run the agent first, then re-run setup_policies.py")
                continue

            # Check if already set up (idempotency guard)
            if await client.agent_has_policies(agent_name):
                print(f"  ↩  Agent '{agent_name}' already has policies assigned. Skipping.")
                print(f"     To reset: bash demo/teardown.sh && bash demo/setup.sh")
                continue

            # Create policy
            print(f"  Creating policy '{policy_name}'...")
            policy_id = await client.create_policy(policy_name)

            # Create controls and add to policy
            print(f"  Creating {len(controls)} controls...")
            for ctrl_name, ctrl_data in controls:
                ctrl_id = await client.create_control(ctrl_name, ctrl_data)
                await client.add_control_to_policy(policy_id, ctrl_id)

            # Assign policy to agent
            print(f"  Assigning policy to agent...")
            await client.assign_policy_to_agent(agent_name, policy_id)
            print(f"  ✓  Policy '{policy_name}' assigned to '{agent_name}'")

    print(f"\n{'='*60}")
    print(f"  Setup complete! All agents are protected.")
    print(f"  Open the control panel: http://localhost:4000")
    print(f"  Run the demo:           python demo_runner.py")
    print(f"{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Setup Agent Control demo policies")
    parser.add_argument("--server", default="http://localhost:8000", help="Agent Control server URL")
    parser.add_argument("--api-key", default=None, help="API key (if auth is enabled)")
    args = parser.parse_args()

    asyncio.run(setup(args.server, args.api_key))


if __name__ == "__main__":
    main()
