#!/usr/bin/env python3
"""
Test script for DocuMind AI query with proper streaming response display.
"""

import requests
import json
import sys
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"
EMAIL = "demo@test.com"
PASSWORD = "demo1234"


def login(email: str, password: str) -> Optional[str]:
    """Login and get JWT token."""
    print("🔐 Logging in...")

    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password}
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ Login successful!\n")
        return token
    else:
        print(f"❌ Login failed: {response.json()}")
        return None


def query_documents(token: str, query: str, session_id: Optional[str] = None):
    """Query documents with streaming response."""
    print(f"📝 Query: {query}\n")
    print("🤖 AI Response:")
    print("=" * 80)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {"query": query}
    if session_id:
        payload["session_id"] = session_id

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/query",
            headers=headers,
            json=payload,
            stream=True
        )

        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
            return

        references_shown = False
        answer_text = ""

        # Process SSE stream
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')

                # SSE format: "data: {json}"
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove 'data: ' prefix

                    try:
                        data = json.loads(data_str)

                        if data['type'] == 'references':
                            if not references_shown:
                                print("\n📚 References:")
                                print("-" * 80)
                                for ref in data['content']:
                                    print(
                                        f"[{ref['index']}] Doc: {ref['doc_id']}")
                                    print(
                                        f"    Preview: {ref['text_preview'][:100]}...")
                                print("-" * 80)
                                print("\n💡 Answer:\n")
                                references_shown = True

                        elif data['type'] == 'token':
                            token_content = data['content']
                            answer_text += token_content
                            print(token_content, end='', flush=True)

                        elif data['type'] == 'done':
                            print("\n")
                            print("=" * 80)
                            print("✅ Query completed successfully!")

                        elif data['type'] == 'error':
                            print(f"\n❌ Error: {data['content']}")

                    except json.JSONDecodeError:
                        continue

    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    except KeyboardInterrupt:
        print("\n\n⚠️  Query interrupted by user")


def main():
    """Main function."""
    print("=" * 80)
    print("🧠 DocuMind AI - Query Testing Script")
    print("=" * 80)
    print()

    # Login
    token = login(EMAIL, PASSWORD)
    if not token:
        sys.exit(1)

    # Get query from command line or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "I am traveling on holiday in a country not in my plan. I have a sudden medical emergency. Will my treatment be covered if I have the Imperial Plan?"

    # Query documents
    query_documents(token, query)

    print("\n" + "=" * 80)
    print("🎯 Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
