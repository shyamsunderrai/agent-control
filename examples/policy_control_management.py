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

import agent_control


async def main() -> None:
    """Demonstrate policy and control management operations."""
    server_url = "http://localhost:8000"

    async with agent_control.AgentControlClient(base_url=server_url) as client:
        print("=" * 70)
        print("Policy and Control Management Example")
        print("=" * 70)
        print()

        # ====================================================================
        # 1. Create a Policy
        # ====================================================================
        print("1️⃣  Creating a new policy...")
        try:
            policy_result = await agent_control.policies.create_policy(
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
            control_result = await agent_control.controls.create_control(
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
        # 3. Add Control to Control Set (previously "Rules to Control")
        # ====================================================================
        print("3️⃣  Adding controls to control set...")
        # Assuming some atomic controls exist with IDs 1, 2, 3
        control_ids = [1, 2, 3]
        # We created a control set (previously called control) in step 2
        control_set_id = control_id  # Variable reuse from step 2 rename
        
        for c_id in control_ids:
            try:
                result = await agent_control.control_sets.add_control_to_control_set(
                    client, control_set_id=control_set_id, control_id=c_id
                )
                if result["success"]:
                    print(f"   ✅ Added control {c_id} to control set {control_set_id}")
            except Exception as e:
                print(f"   ⚠️  Control {c_id}: {e}")
        print()

        # ====================================================================
        # 4. List Control Set Controls
        # ====================================================================
        print("4️⃣  Listing control set controls...")
        try:
            result = await agent_control.control_sets.list_control_set_controls(client, control_set_id)
            list_control_ids = result["control_ids"]
            print(f"   📋 Control Set {control_set_id} has {len(list_control_ids)} controls: {list_control_ids}")
        except Exception as e:
            print(f"   ❌ Failed to list controls: {e}")
        print()

        # ====================================================================
        # 5. Add Control Set to Policy
        # ====================================================================
        print("5️⃣  Adding control set to policy...")
        try:
            result = await agent_control.policies.add_control_set_to_policy(
                client, policy_id=policy_id, control_set_id=control_set_id
            )
            if result["success"]:
                print(f"   ✅ Added control set {control_set_id} to policy {policy_id}")
        except Exception as e:
            print(f"   ❌ Failed to add control set to policy: {e}")
        print()

        # ====================================================================
        # 6. List Policy Control Sets
        # ====================================================================
        print("6️⃣  Listing policy control sets...")
        try:
            result = await agent_control.policies.list_policy_control_sets(client, policy_id)
            list_cs_ids = result["control_set_ids"]
            print(f"   📋 Policy {policy_id} has {len(list_cs_ids)} control sets: {list_cs_ids}")
        except Exception as e:
            print(f"   ❌ Failed to list control sets: {e}")
        print()

        # ====================================================================
        # 7. Remove Control from Control Set (Optional - Cleanup)
        # ====================================================================
        print("7️⃣  Removing a control from control set (cleanup)...")
        try:
            # Remove the last control we added
            result = await agent_control.control_sets.remove_control_from_control_set(
                client, control_set_id=control_set_id, control_id=control_ids[-1]
            )
            if result["success"]:
                print(f"   ✅ Removed control {control_ids[-1]} from control set {control_set_id}")
        except Exception as e:
            print(f"   ⚠️  Failed to remove control: {e}")
        print()

        # ====================================================================
        # 8. Remove Control Set from Policy (Optional - Cleanup)
        # ====================================================================
        print("8️⃣  Removing control set from policy (cleanup)...")
        try:
            result = await agent_control.policies.remove_control_set_from_policy(
                client, policy_id=policy_id, control_set_id=control_set_id
            )
            if result["success"]:
                print(f"   ✅ Removed control set {control_set_id} from policy {policy_id}")
        except Exception as e:
            print(f"   ⚠️  Failed to remove control set from policy: {e}")
        print()

        # ====================================================================
        # 9. Verify Removal
        # ====================================================================
        print("9️⃣  Verifying removals...")
        try:
            # Check control set controls after removal
            result = await agent_control.control_sets.list_control_set_controls(client, control_set_id)
            ids_after = result["control_ids"]
            print(f"   📋 Control Set {control_set_id} now has {len(ids_after)} controls")

            # Check policy control sets after removal
            result = await agent_control.policies.list_policy_control_sets(client, policy_id)
            cs_ids_after = result["control_set_ids"]
            print(f"   📋 Policy {policy_id} now has {len(cs_ids_after)} control sets")
        except Exception as e:
            print(f"   ❌ Failed to verify removals: {e}")
        print()

        print("=" * 70)
        print("Example completed!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

