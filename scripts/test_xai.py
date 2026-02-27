import os
import sys
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import web_search

def main():
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        print("XAI_API_KEY not set")
        sys.exit(1)
        
    client = Client(api_key=api_key)
    chat = client.chat.create(
        model="grok-4-1-fast-reasoning",
        tools=[web_search()],
        include=["verbose_streaming"],
    )

    chat.append(user("What is xAI? Provide a short answer."))

    is_thinking = True
    response_obj = None
    for response, chunk in chat.stream():
        response_obj = response
        for tool_call in chunk.tool_calls:
            print("Calling tool:", tool_call.function.name)
        if response.usage and response.usage.reasoning_tokens and is_thinking:
            print(f"\rThinking... ({response.usage.reasoning_tokens} tokens)", end="", flush=True)
        if chunk.content and is_thinking:
            print("\n\nFinal Response:")
            is_thinking = False
        if chunk.content and not is_thinking:
            print(chunk.content, end="", flush=True)

    print("\n\nCitations:")
    if response_obj and hasattr(response_obj, 'citations'):
        print(response_obj.citations)
    else:
        print("No citations found in response.")

if __name__ == "__main__":
    main()
