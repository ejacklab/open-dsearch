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

    chat.append(user("What is xAI?"))

    response_obj = None
    for response, chunk in chat.stream():
        response_obj = response

    print("--- Citations ---")
    if response_obj and hasattr(response_obj, 'citations'):
        print(type(response_obj.citations))
        for c in response_obj.citations:
            print(f"Title: {c.title}")
            print(f"URL: {c.url}")
            print(f"Snippet: {c.snippet}")
    else:
        print("No citations found.")

if __name__ == "__main__":
    main()
