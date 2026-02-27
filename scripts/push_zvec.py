#!/usr/bin/env python3
"""
Push search results to zvec vector database.
Usage: python push_zvec.py "title" "url" "snippet" "topic"
Or: cat results.json | python push_zvec.py --stdin
"""

import sys
import json
import os
import subprocess

ZVEC_AVAILABLE = False
try:
    import zvec

    ZVEC_AVAILABLE = True
except ImportError:
    print("zvec not installed - using file fallback", file=sys.stderr)


def get_embedding(text: str) -> list:
    """Get embedding using Gemini API"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = os.environ.get("MINIMAX_API_KEY")

    if not api_key:
        return [0.0] * 768

    try:
        import requests
    except ImportError:
        return [0.0] * 768

    # Try Gemini embedding
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={api_key}"
        body = {"content": {"role": "parts", "parts": [{"text": text[:1000]}]}}
        resp = requests.post(url, json=body, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("embedding", {}).get("values", [0.0] * 768)
    except:
        pass

    return [0.0] * 768


def push_to_zvec(title: str, url: str, snippet: str, topic: str):
    """Push a single result to zvec"""

    if not ZVEC_AVAILABLE:
        # Fallback: append to JSON file
        file_path = f"{topic.replace(' ', '_')}_vectors.jsonl"
        embedding = get_embedding(f"{title}. {snippet}")
        data = {
            "title": title,
            "url": url,
            "snippet": snippet,
            "topic": topic,
            "embedding": embedding,
        }
        with open(file_path, "a") as f:
            f.write(json.dumps(data) + "\n")
        print(f"✓ Indexed (file): {title[:40]}...")
        return

    try:
        # Try to open existing collection
        try:
            collection = zvec.open("./zvec_data")
        except:
            schema = zvec.CollectionSchema(
                name="research",
                vectors=zvec.VectorSchema("embedding", zvec.DataType.VECTOR_FP32, 768),
            )
            collection = zvec.create_and_open(path="./zvec_data", schema=schema)

        # Get embedding
        text = f"{title}. {snippet}"
        embedding = get_embedding(text)

        # Insert to zvec
        doc_id = (
            url.replace("https://", "").replace("http://", "").replace("/", "_")[:100]
        )
        collection.insert(
            [
                zvec.Doc(
                    id=doc_id,
                    vectors={"embedding": embedding},
                    payload={
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "topic": topic,
                    },
                )
            ]
        )

        print(f"✓ Indexed: {title[:40]}...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def main():
    if "--stdin" in sys.argv:
        # Read from stdin (JSON lines)
        for line in sys.stdin:
            try:
                data = json.loads(line.strip())
                push_to_zvec(
                    data.get("title", ""),
                    data.get("url", ""),
                    data.get("snippet", ""),
                    data.get("topic", "research"),
                )
            except:
                pass
    elif len(sys.argv) >= 5:
        title = sys.argv[1]
        url = sys.argv[2]
        snippet = sys.argv[3]
        topic = sys.argv[4]
        push_to_zvec(title, url, snippet, topic)
    else:
        # Try to read from stdin
        try:
            data = json.loads(sys.stdin.read())
            push_to_zvec(
                data.get("title", ""),
                data.get("url", ""),
                data.get("snippet", ""),
                data.get("topic", "research"),
            )
        except:
            print(
                "Usage: python push_zvec.py <title> <url> <snippet> <topic>",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
