"""
Test script to verify the accuracy improvements in DocuMind AI
Run this after uploading documents to test the enhanced retrieval
"""

import requests
import json

API_URL = "http://localhost:8000"

# Test queries that benefit from the improvements
test_queries = [
    {
        "name": "Definition Query",
        "query": "What is a newborn baby according to the policy?",
        "expected": "Should find definition with 90 days specification"
    },
    {
        "name": "Exclusion Query",
        "query": "What medical procedures are NOT covered?",
        "expected": "Should identify exclusions and limitations"
    },
    {
        "name": "Coverage Query",
        "query": "What is covered for maternity?",
        "expected": "Should find both coverage AND exclusions"
    },
    {
        "name": "Complex Technical Query",
        "query": "What is the pre-hospitalization coverage period for international travel?",
        "expected": "Should find specific clause with exact numbers"
    },
    {
        "name": "Eligibility Query",
        "query": "Am I eligible for coverage if I have a pre-existing condition?",
        "expected": "Should find pre-existing condition clauses"
    }
]


def test_query(token: str, query: str):
    """Test a single query and show results"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {"query": query}

    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    print(f"{'='*80}\n")

    try:
        response = requests.post(
            f"{API_URL}/api/v1/chat/query",
            headers=headers,
            json=payload,
            stream=True
        )

        answer = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        if data['type'] == 'token':
                            answer += data['content']
                            print(data['content'], end='', flush=True)
                        elif data['type'] == 'references':
                            print(
                                f"\n[References: {len(data['content'])} chunks retrieved]")
                    except json.JSONDecodeError:
                        pass

        print("\n")
        return answer

    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    """Main test function"""
    print("🔍 DocuMind AI - Accuracy Test Suite")
    print("=" * 80)

    # Get token (you'll need to provide this)
    token = input("\nEnter your JWT token (or press Enter to skip): ").strip()

    if not token:
        print("\n⚠️  No token provided. Please:")
        print("1. Login to DocuMind AI")
        print("2. Copy your JWT token")
        print("3. Run this script again")
        print("\nOr use the API directly:")
        print(f"curl -X POST {API_URL}/api/v1/auth/login \\")
        print('  -H "Content-Type: application/json" \\')
        print(
            '  -d \'{"email": "your@email.com", "password": "yourpassword"}\'')
        return

    print("\n✅ Token received. Starting tests...\n")

    # Run all test queries
    for i, test in enumerate(test_queries, 1):
        print(f"\n📋 Test {i}/{len(test_queries)}: {test['name']}")
        print(f"Expected: {test['expected']}")

        answer = test_query(token, test['query'])

        if answer:
            print(f"\n✓ Test completed ({len(answer)} chars)")
        else:
            print(f"\n✗ Test failed")

        input("\nPress Enter to continue to next test...")

    print("\n" + "=" * 80)
    print("🎉 All tests completed!")
    print("\nKey improvements to look for:")
    print("  ✓ More accurate retrieval of specific information")
    print("  ✓ Better handling of exclusions and limitations")
    print("  ✓ Precise definitions with exact numbers/timeframes")
    print("  ✓ Comprehensive answers that cover multiple aspects")
    print("  ✓ Natural citations of specific clauses/sections")
    print("=" * 80)


if __name__ == "__main__":
    main()
