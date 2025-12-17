import asyncio
import os
import random
import sys
import uuid

# Use local SDK path
sys.path.append(os.path.join(os.path.dirname(__file__), "../sdks/python/src"))

from agent_control import (
    AgentControlClient,
    ControlAction,
    ControlDefinition,
    ControlSelector,
    EvaluatorConfig,
    control_sets,
    controls,
    policies,
)

# Convert agent_id to UUID5 to match what the SDK init() does internally
# In a real scenario, you might just use a hardcoded UUID or fetch it from the server
AGENT_ID_STR = "chatbot-v1"
AGENT_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, AGENT_ID_STR))

async def setup_controls():
    async with AgentControlClient(base_url="http://localhost:8000") as client:
        print(f"🔧 Configuring Security Rules for Agent: {AGENT_ID_STR} ({AGENT_UUID})")

        # 1. Create/Get Policy
        policy_name = "content-safety-policy"
        try:
            policy = await policies.create_policy(client, policy_name)
            policy_id = policy["policy_id"]
            print(f"✅ Created Policy: {policy_name} (ID: {policy_id})")
        except Exception:
            # Simple fallback for demo: create a new random one if name collision
            # In production, you'd lookup by name.
            policy_name = f"content-safety-policy-{random.randint(1000,9999)}"
            policy = await policies.create_policy(client, policy_name)
            policy_id = policy["policy_id"]
            print(f"✅ Created Policy: {policy_name} (ID: {policy_id})")

        # 2. Create/Get Control Set
        cs_name = "chat-controls"
        try:
            cs = await control_sets.create_control_set(client, cs_name)
            cs_id = cs["control_set_id"]
            print(f"✅ Created Control Set: {cs_name} (ID: {cs_id})")
        except Exception:
            cs_name = f"chat-controls-{random.randint(1000,9999)}"
            cs = await control_sets.create_control_set(client, cs_name)
            cs_id = cs["control_set_id"]
            print(f"✅ Created Control Set: {cs_name} (ID: {cs_id})")

        # 3. Create/Get "Block Bad Words" Control
        c_name = "block-bad-words"
        try:
            c = await controls.create_control(client, c_name)
            c_id = c["control_id"]
            print(f"✅ Created Control: {c_name} (ID: {c_id})")
        except Exception:
            c_name = f"block-bad-words-{random.randint(1000,9999)}"
            c = await controls.create_control(client, c_name)
            c_id = c["control_id"]
            print(f"✅ Created Control: {c_name} (ID: {c_id})")

        # 4. Configure Control Data (This is what you tweak!)
        # CHANGE THIS LIST and re-run this script to update rules dynamically
        banned_words = ["forbidden", "secret"]

        print(f"📝 Updating rules: Blocking words {banned_words}")

        control_data = ControlDefinition(
            description="Block usage of banned words in input",
            enabled=True,
            applies_to="llm_call",
            check_stage="pre",
            selector=ControlSelector(path="input"),
            evaluator=EvaluatorConfig(
                plugin="list",
                config={
                    "values": banned_words,
                    "logic": "any",
                    "match_mode": "contains",
                    "case_sensitive": False
                }
            ),
            action=ControlAction(decision="deny")
        )

        await controls.set_control_data(client, c_id, control_data)
        print("✅ Control configuration updated.")

        # 5. Link everything (Idempotent operations)
        await control_sets.add_control_to_control_set(client, cs_id, c_id)
        await policies.add_control_set_to_policy(client, policy_id, cs_id)

        # 6. Assign to Agent
        await policies.assign_policy_to_agent(client, AGENT_UUID, policy_id)
        print("✅ Policy assigned to Agent. Rules are live!")

if __name__ == "__main__":
    asyncio.run(setup_controls())

