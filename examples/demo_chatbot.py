import asyncio
import os
import sys

# Use local SDK path
sys.path.append(os.path.join(os.path.dirname(__file__), "../sdks/python/src"))

import agent_control
from agent_control import ControlViolationError, control


# Mock OpenAI for demonstration
class MockOpenAI:
    class Chat:
        class Completions:
            async def create(self, messages, **kwargs):
                last_msg = messages[-1]["content"]
                return type('obj', (object,), {
                    "choices": [type('obj', (object,), {
                        "message": type('obj', (object,), {
                            "content": f"Echo: {last_msg}"
                        })()
                    })()]
                })()

        def __init__(self):
            self.completions = self.Completions()

    def __init__(self, api_key=None):
        self.chat = self.Chat()

# Initialize Agent
# IMPORTANT: This ID must match the one in demo_setup_controls.py
AGENT_ID = "chatbot-v1"

agent = agent_control.init(
    agent_name="Secure Chatbot",
    agent_id=AGENT_ID,
    agent_description="A chatbot with content filtering policy",
    server_url="http://localhost:8000"
)

# Chat function to be protected
@control()
async def chat(user_input: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=api_key)
        except ImportError:
            print("⚠️  OPENAI_API_KEY found but 'openai' package not installed. Using mock.")
            client = MockOpenAI(api_key="mock")
    else:
        # print("ℹ️  No OPENAI_API_KEY set. Using mock response.")
        client = MockOpenAI(api_key="mock")

    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": user_input}]
    )
    return response.choices[0].message.content

async def run_chat_loop():
    print(f"\n🤖 Agent '{AGENT_ID}' is online and listening for messages.")
    print("   (Rules are fetched from the server on every request)")

    # Interactive Chat Loop
    print("\n💬 Starting Interactive Chat Session")
    print("   Type 'exit' or 'quit' to end the session.")

    while True:
        try:
            user_input = input("\nUser: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print("👋 Goodbye!")
                break

            if not user_input:
                continue

            # We call the decorated function.
            # The decorator will check with the server before executing.
            response = await chat(user_input)
            print(f"Bot: {response}")

        except ControlViolationError:
            print("⛔ Blocked: Policy violation detected.")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run_chat_loop())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

