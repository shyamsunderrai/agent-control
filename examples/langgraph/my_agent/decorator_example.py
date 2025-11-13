"""
Visual demonstration of how the @protect decorator extracts and passes data.

Run this file to see exactly what data is available at each stage.
"""

import asyncio
from pathlib import Path
from protect_engine import protect, init_protect_engine, RuleViolation

# Initialize the engine
rules_file = Path(__file__).parent / "rules.yaml"
init_protect_engine(rules_file)


print("=" * 80)
print("DEMONSTRATION: How @protect Decorator Extracts Data")
print("=" * 80)
print()


# ============================================================================
# EXAMPLE 1: Basic Input Extraction
# ============================================================================
print("EXAMPLE 1: Basic Input Extraction")
print("-" * 80)

@protect('input-validation', input='user_message')
async def example1(user_message: str):
    """
    Decorator mapping:
        input='user_message'
        
    This means: Extract the 'user_message' parameter and check it as 'input'
    """
    return f"Processed: {user_message}"

print("Code:")
print("""
@protect('input-validation', input='user_message')
async def example1(user_message: str):
    return f"Processed: {user_message}"
""")

print("Function call:")
print("  result = await example1('Hello World')")
print()

print("What the decorator sees:")
print("  Function arguments: user_message='Hello World'")
print("  Data mapping: input='user_message'")
print("  ↓")
print("  Extracted data = {'input': 'Hello World'}")
print()

print("YAML rule can check:")
print("  data: input  ← This will check 'Hello World'")
print()
print()


# ============================================================================
# EXAMPLE 2: Multiple Parameters
# ============================================================================
print("EXAMPLE 2: Multiple Parameters")
print("-" * 80)

@protect('business-validation',
         input='action',
         context='user_info',
         metadata='req_meta')
async def example2(action: str, user_info: dict, req_meta: dict):
    """
    Decorator mapping:
        input='action'
        context='user_info'
        metadata='req_meta'
    """
    return f"Action: {action}"

print("Code:")
print("""
@protect('business-validation',
         input='action',
         context='user_info',
         metadata='req_meta')
async def example2(action: str, user_info: dict, req_meta: dict):
    return f"Action: {action}"
""")

print("Function call:")
print("""  result = await example2(
      'delete_account',
      {'user_id': '123', 'tier': 'free'},
      {'ip': '1.2.3.4'}
  )""")
print()

print("What the decorator sees:")
print("  Function arguments:")
print("    action='delete_account'")
print("    user_info={'user_id': '123', 'tier': 'free'}")
print("    req_meta={'ip': '1.2.3.4'}")
print()

print("  Data mappings:")
print("    input='action' → Extract 'action' parameter")
print("    context='user_info' → Extract 'user_info' parameter")
print("    metadata='req_meta' → Extract 'req_meta' parameter")
print("  ↓")
print("  Extracted data = {")
print("      'input': 'delete_account',")
print("      'context': {'user_id': '123', 'tier': 'free'},")
print("      'metadata': {'ip': '1.2.3.4'}")
print("  }")
print()

print("YAML rule can check:")
print("  data: input    ← Checks 'delete_account'")
print("  data: context  ← Checks {'user_id': '123', 'tier': 'free'}")
print("  data: metadata ← Checks {'ip': '1.2.3.4'}")
print()
print()


# ============================================================================
# EXAMPLE 3: Output Validation (Special Case)
# ============================================================================
print("EXAMPLE 3: Output Validation")
print("-" * 80)

@protect('output-filter', input='query', output='response')
async def example3(query: str) -> str:
    """
    Decorator mapping:
        input='query'
        output='response' ← Special! Captures return value
    """
    # Simulate LLM response with PII
    return f"User query: {query}. SSN: 123-45-6789, Email: user@example.com"

print("Code:")
print("""
@protect('output-filter', input='query', output='response')
async def example3(query: str) -> str:
    return "User query: {query}. SSN: 123-45-6789, Email: user@example.com"
""")

print("Function call:")
print("  result = await example3('Get user info')")
print()

print("What happens (TWO stages):")
print()
print("  STAGE 1 - BEFORE function execution:")
print("    Extracted data = {'input': 'Get user info'}")
print("    Rules with data: input are checked")
print()
print("  STAGE 2 - Function executes and returns:")
print("    Return value = 'User query: Get user info. SSN: 123-45-6789, ...'")
print()
print("  STAGE 3 - AFTER function execution:")
print("    Extracted data = {")
print("        'input': 'Get user info',")
print("        'output': 'User query: ... SSN: 123-45-6789, ...'  ← Return value")
print("    }")
print("    Rules with data: output are checked")
print("    ↓")
print("    If rule has action: redact, output is transformed")
print("    ↓")
print("    Return value = 'User query: ... SSN: [REDACTED], ...'")
print()
print()


# ============================================================================
# EXAMPLE 4: LangGraph State Extraction
# ============================================================================
print("EXAMPLE 4: LangGraph State Extraction")
print("-" * 80)

from typing import TypedDict

class AgentState(TypedDict):
    messages: list
    context: dict
    history: list

@protect('message-validation',
         messages='state_dict',  # We'll extract from the state parameter
         context='state_dict')
async def example4(state_dict: AgentState):
    """
    For complex state objects, you extract the whole state
    and YAML rules can access nested fields
    """
    return {"messages": state_dict["messages"] + ["response"]}

print("Code:")
print("""
class AgentState(TypedDict):
    messages: list
    context: dict

@protect('message-validation',
         messages='state_dict',
         context='state_dict')
async def example4(state_dict: AgentState):
    return {"messages": state_dict["messages"] + ["response"]}
""")

print("Function call:")
print("""  result = await example4({
      'messages': [{'role': 'user', 'content': 'Hello'}],
      'context': {'user_id': '123'}
  })""")
print()

print("What the decorator sees:")
print("  Function arguments:")
print("    state_dict={")
print("        'messages': [{'role': 'user', 'content': 'Hello'}],")
print("        'context': {'user_id': '123'}")
print("    }")
print()

print("  Data mappings:")
print("    messages='state_dict' → Extract entire state_dict")
print("    context='state_dict' → Extract entire state_dict (same)")
print("  ↓")
print("  Extracted data = {")
print("      'messages': {'messages': [...], 'context': {...}},")
print("      'context': {'messages': [...], 'context': {...}}")
print("  }")
print()

print("Note: When you pass the same parameter multiple times,")
print("      the YAML matching logic extracts the relevant parts.")
print()
print()


# ============================================================================
# EXAMPLE 5: What You CANNOT Access
# ============================================================================
print("EXAMPLE 5: What You CANNOT Access")
print("-" * 80)

print("❌ Local variables are NOT accessible:")
print("""
@protect('step', input='processed_text')  # Won't work!
async def bad_example1(text: str):
    processed_text = text.upper()  # Local variable
    return processed_text
""")
print("Problem: 'processed_text' is not a function parameter")
print()

print("❌ Mismatched parameter names:")
print("""
@protect('step', input='user_input')  # Won't work!
async def bad_example2(message: str):  # Parameter is 'message'
    return message
""")
print("Problem: Looking for 'user_input' but parameter is 'message'")
print()

print("✅ Correct way:")
print("""
@protect('step', input='message')  # ✓ Matches parameter name
async def good_example(message: str):
    return message
""")
print()
print()


# ============================================================================
# EXAMPLE 6: Real Execution with Rule Checking
# ============================================================================
print("EXAMPLE 6: Real Execution with Rule Checking")
print("-" * 80)

async def demonstrate_real_execution():
    """Actually run the decorated functions to show what happens."""
    
    # Test 1: Safe input
    print("Test 1: Safe input")
    print("  Calling: await example1('Safe message')")
    try:
        result = await example1("Safe message")
        print(f"  ✓ Result: {result}")
    except RuleViolation as e:
        print(f"  ✗ Blocked: {e.message}")
    print()
    
    # Test 2: Input with restricted name (should fail)
    print("Test 2: Input with restricted name")
    print("  Calling: await example1('Message from Nachiket')")
    try:
        result = await example1("Message from Nachiket")
        print(f"  ✓ Result: {result}")
    except RuleViolation as e:
        print(f"  ✗ Blocked: {e.message}")
    print()
    
    # Test 3: Multiple parameters
    print("Test 3: Multiple parameters")
    print("  Calling: await example2('view_data', {'tier': 'premium'}, {'ip': '1.1.1.1'})")
    try:
        result = await example2("view_data", {"tier": "premium"}, {"ip": "1.1.1.1"})
        print(f"  ✓ Result: {result}")
    except RuleViolation as e:
        print(f"  ✗ Blocked: {e.message}")
    print()

print("Running actual executions:")
print("-" * 40)
asyncio.run(demonstrate_real_execution())


# ============================================================================
# Summary
# ============================================================================
print()
print("=" * 80)
print("SUMMARY: What Information Is Available")
print("=" * 80)
print()

print("✓ You CAN access:")
print("  • Any function parameter (by name)")
print("  • Default parameter values (automatically applied)")
print("  • Function return value (via output mapping)")
print("  • Nested data structures (dicts, lists in parameters)")
print()

print("✗ You CANNOT access:")
print("  • Local variables inside the function")
print("  • Variables from outer scope")
print("  • Intermediate computation results")
print("  • Parameters not explicitly mapped in @protect(...)")
print()

print("Key Pattern:")
print("  @protect('step-id', data_type='parameter_name')")
print("           ↓         ↓          ↓")
print("        step_id   what it's   actual function")
print("        in YAML   called in   parameter name")
print("                  YAML rules")
print()

print("=" * 80)

