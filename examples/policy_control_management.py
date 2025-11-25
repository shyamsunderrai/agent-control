"""
Example: Policy and Control Management with Agent Protect SDK

This example demonstrates how to use the Agent Protect SDK to:
1. Create policies and controls
2. Associate rules with controls
3. Associate controls with policies
4. List policy controls and control rules
5. Remove associations

Prerequisites:
- Agent Protect server running (default: http://localhost:8000)
- Database initialized with some rules

Usage:
    python examples/policy_control_management.py
"""

import asyncio

import agent_protect


async def main() -> None:
    """Demonstrate policy and control management operations."""
    server_url = "http://localhost:8000"

    async with agent_protect.AgentProtectClient(base_url=server_url) as client:
        print("=" * 70)
        print("Policy and Control Management Example")
        print("=" * 70)
        print()

        # ====================================================================
        # 1. Create a Policy
        # ====================================================================
        print("1️⃣  Creating a new policy...")
        try:
            policy_result = await agent_protect.policies.create_policy(
                client, "production-policy"
            )
            policy_id = policy_result["policy_id"]
            print(f"   ✅ Created policy with ID: {policy_id}")
        except Exception as e:
            print(f"   ❌ Failed to create policy: {e}")
            # If policy already exists, try to use it (for demo purposes)
            policy_id = 1  # Assume ID 1 exists
            print(f"   ℹ️  Using existing policy ID: {policy_id}")
        print()

        # ====================================================================
        # 2. Create a Control
        # ====================================================================
        print("2️⃣  Creating a new control...")
        try:
            control_result = await agent_protect.controls.create_control(
                client, "pii-protection"
            )
            control_id = control_result["control_id"]
            print(f"   ✅ Created control with ID: {control_id}")
        except Exception as e:
            print(f"   ❌ Failed to create control: {e}")
            # If control already exists, try to use it (for demo purposes)
            control_id = 1  # Assume ID 1 exists
            print(f"   ℹ️  Using existing control ID: {control_id}")
        print()

        # ====================================================================
        # 3. Add Rules to Control
        # ====================================================================
        print("3️⃣  Adding rules to control...")
        # Assuming some rules exist with IDs 1, 2, 3
        rule_ids = [1, 2, 3]
        for rule_id in rule_ids:
            try:
                result = await agent_protect.controls.add_rule_to_control(
                    client, control_id=control_id, rule_id=rule_id
                )
                if result["success"]:
                    print(f"   ✅ Added rule {rule_id} to control {control_id}")
            except Exception as e:
                print(f"   ⚠️  Rule {rule_id}: {e}")
        print()

        # ====================================================================
        # 4. List Control Rules
        # ====================================================================
        print("4️⃣  Listing control rules...")
        try:
            result = await agent_protect.controls.list_control_rules(client, control_id)
            rule_ids = result["rule_ids"]
            print(f"   📋 Control {control_id} has {len(rule_ids)} rules: {rule_ids}")
        except Exception as e:
            print(f"   ❌ Failed to list rules: {e}")
        print()

        # ====================================================================
        # 5. Add Control to Policy
        # ====================================================================
        print("5️⃣  Adding control to policy...")
        try:
            result = await agent_protect.policies.add_control_to_policy(
                client, policy_id=policy_id, control_id=control_id
            )
            if result["success"]:
                print(f"   ✅ Added control {control_id} to policy {policy_id}")
        except Exception as e:
            print(f"   ❌ Failed to add control to policy: {e}")
        print()

        # ====================================================================
        # 6. List Policy Controls
        # ====================================================================
        print("6️⃣  Listing policy controls...")
        try:
            result = await agent_protect.policies.list_policy_controls(client, policy_id)
            control_ids = result["control_ids"]
            print(f"   📋 Policy {policy_id} has {len(control_ids)} controls: {control_ids}")
        except Exception as e:
            print(f"   ❌ Failed to list controls: {e}")
        print()

        # ====================================================================
        # 7. Remove Rule from Control (Optional - Cleanup)
        # ====================================================================
        print("7️⃣  Removing a rule from control (cleanup)...")
        try:
            # Remove the last rule we added
            result = await agent_protect.controls.remove_rule_from_control(
                client, control_id=control_id, rule_id=rule_ids[-1]
            )
            if result["success"]:
                print(f"   ✅ Removed rule {rule_ids[-1]} from control {control_id}")
        except Exception as e:
            print(f"   ⚠️  Failed to remove rule: {e}")
        print()

        # ====================================================================
        # 8. Remove Control from Policy (Optional - Cleanup)
        # ====================================================================
        print("8️⃣  Removing control from policy (cleanup)...")
        try:
            result = await agent_protect.policies.remove_control_from_policy(
                client, policy_id=policy_id, control_id=control_id
            )
            if result["success"]:
                print(f"   ✅ Removed control {control_id} from policy {policy_id}")
        except Exception as e:
            print(f"   ⚠️  Failed to remove control from policy: {e}")
        print()

        # ====================================================================
        # 9. Verify Removal
        # ====================================================================
        print("9️⃣  Verifying removals...")
        try:
            # Check control rules after removal
            result = await agent_protect.controls.list_control_rules(client, control_id)
            rule_ids_after = result["rule_ids"]
            print(f"   📋 Control {control_id} now has {len(rule_ids_after)} rules")

            # Check policy controls after removal
            result = await agent_protect.policies.list_policy_controls(client, policy_id)
            control_ids_after = result["control_ids"]
            print(f"   📋 Policy {policy_id} now has {len(control_ids_after)} controls")
        except Exception as e:
            print(f"   ❌ Failed to verify removals: {e}")
        print()

        print("=" * 70)
        print("Example completed!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

