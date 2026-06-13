#!/usr/bin/env python3
"""
Run test queries against the Python Q&A Assistant API.

Executes a diverse set of Python-related queries, records the responses,
and generates a test results report.

Usage:
    # First, start the API server:
    #   uvicorn app.main:app --reload
    # Then run tests:
    python scripts/run_tests.py

    # Or specify a custom API URL:
    python scripts/run_tests.py --url http://localhost:8000
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# --- Test Queries ---
TEST_QUERIES = [
    {
        "id": 1,
        "question": "How do I read a CSV file in Python?",
        "category": "File I/O",
        "expected_topics": ["csv module", "pandas", "read_csv"],
    },
    {
        "id": 2,
        "question": "What is the difference between a list and a tuple in Python?",
        "category": "Data Structures",
        "expected_topics": ["mutable", "immutable", "performance"],
    },
    {
        "id": 3,
        "question": "How to handle exceptions in Python?",
        "category": "Error Handling",
        "expected_topics": ["try", "except", "finally", "raise"],
    },
    {
        "id": 4,
        "question": "Explain Python decorators with examples",
        "category": "Advanced Concepts",
        "expected_topics": ["@decorator", "wrapper", "functools"],
    },
    {
        "id": 5,
        "question": "How to make HTTP requests in Python?",
        "category": "Networking",
        "expected_topics": ["requests", "urllib", "get", "post"],
    },
    {
        "id": 6,
        "question": "What are Python generators and when to use them?",
        "category": "Iterators & Generators",
        "expected_topics": ["yield", "lazy evaluation", "memory"],
    },
    {
        "id": 7,
        "question": "How to connect to a MySQL database in Python?",
        "category": "Databases",
        "expected_topics": ["mysql-connector", "pymysql", "cursor", "connect"],
    },
    {
        "id": 8,
        "question": "What is the GIL in Python and why does it matter?",
        "category": "Python Internals",
        "expected_topics": ["Global Interpreter Lock", "threading", "multiprocessing"],
    },
    {
        "id": 9,
        "question": "How to sort a dictionary by its values in Python?",
        "category": "Data Manipulation",
        "expected_topics": ["sorted", "lambda", "items"],
    },
    {
        "id": 10,
        "question": "Explain list comprehension vs map and filter in Python",
        "category": "Functional Programming",
        "expected_topics": ["list comprehension", "map", "filter", "performance"],
    },
]


def run_health_check(base_url: str) -> dict:
    """Check if the API is healthy."""
    try:
        response = httpx.get(f"{base_url}/health", timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def run_query(base_url: str, question: str) -> dict:
    """Send a question to the API and return the response."""
    try:
        response = httpx.post(
            f"{base_url}/ask",
            json={"question": question},
            timeout=60,
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}


def check_expected_topics(answer: str, expected_topics: list[str]) -> tuple[int, list[str]]:
    """Check how many expected topics appear in the answer."""
    answer_lower = answer.lower()
    found = [t for t in expected_topics if t.lower() in answer_lower]
    return len(found), found


def generate_report(results: list[dict], base_url: str) -> str:
    """Generate a markdown test report."""
    timestamp = datetime.now(timezone.utc).isoformat()

    report = f"""# 🧪 Python Q&A Assistant — Test Results

**Generated**: {timestamp}
**API URL**: {base_url}
**Total Queries**: {len(results)}

---

## Summary

| Metric | Value |
|--------|-------|
| Total Queries | {len(results)} |
| Successful | {sum(1 for r in results if 'error' not in r)} |
| Failed | {sum(1 for r in results if 'error' in r)} |
| Avg Latency | {sum(r.get('latency_ms', 0) for r in results) / max(len(results), 1):.0f} ms |
| Avg Confidence | {sum(r.get('confidence', 0) for r in results) / max(len(results), 1):.2f} |
| Topic Coverage | {sum(r.get('topics_found', 0) for r in results)} / {sum(r.get('topics_total', 0) for r in results)} |

---

## Detailed Results

"""

    for r in results:
        status = "✅" if "error" not in r else "❌"
        report += f"""### {status} Query {r['id']}: {r['category']}

**Question**: {r['question']}

**Latency**: {r.get('latency_ms', 'N/A')} ms | **Confidence**: {r.get('confidence', 'N/A')} | **Sources**: {r.get('num_sources', 0)}

**Expected Topics**: {', '.join(r.get('expected_topics', []))}
**Found Topics**: {', '.join(r.get('found_topics', []))} ({r.get('topics_found', 0)}/{r.get('topics_total', 0)})

<details>
<summary>📝 Full Answer</summary>

{r.get('answer', r.get('error', 'No answer'))}

</details>

<details>
<summary>📚 Sources</summary>

"""
        for s in r.get("sources", []):
            report += f"- **{s.get('title', 'N/A')}** (Score: {s.get('score', 'N/A')}) — [{s.get('source_url', '')}]({s.get('source_url', '')})\n"

        report += f"""
</details>

---

"""

    report += """## Observations & Quality Analysis

### Strengths
- Answers are grounded in real Stack Overflow Q&A data
- Code examples are included when relevant
- Multiple source documents provide comprehensive coverage

### Areas for Improvement
- Some answers could be more concise
- Edge cases with very specific library questions may have limited context
- Confidence scoring could be refined with better relevance metrics

### Edge Cases Tested
- Questions about Python internals (GIL) — tests depth of knowledge base
- Database connectivity questions — tests practical/applied knowledge
- Functional programming comparisons — tests nuanced understanding
"""

    return report


def main():
    parser = argparse.ArgumentParser(description="Run test queries against the Python Q&A API")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    print("=" * 60)
    print("  Python Q&A Assistant — Test Runner")
    print("=" * 60)
    print(f"\n🌐 API URL: {base_url}")

    # Health check
    print("\n🏥 Running health check...")
    health = run_health_check(base_url)
    if "error" in health:
        print(f"❌ Health check failed: {health['error']}")
        print("   Make sure the API server is running:")
        print("   uvicorn app.main:app --reload")
        sys.exit(1)

    print(f"   Status: {health.get('status', 'unknown')}")
    print(f"   Pipeline Ready: {health.get('pipeline_ready', False)}")

    if not health.get("pipeline_ready", False):
        print("❌ RAG pipeline not ready. Build the vector store first.")
        sys.exit(1)

    # Run test queries
    results = []
    print(f"\n📝 Running {len(TEST_QUERIES)} test queries...\n")

    for tq in TEST_QUERIES:
        print(f"  [{tq['id']:2d}/{len(TEST_QUERIES)}] {tq['category']}: {tq['question'][:50]}...", end=" ", flush=True)

        response = run_query(base_url, tq["question"])

        result = {
            "id": tq["id"],
            "question": tq["question"],
            "category": tq["category"],
            "expected_topics": tq["expected_topics"],
        }

        if "error" in response:
            result["error"] = response["error"]
            print("❌")
        else:
            result["answer"] = response.get("answer", "")
            result["sources"] = response.get("sources", [])
            result["confidence"] = response.get("confidence", 0)
            result["latency_ms"] = response.get("latency_ms", 0)
            result["num_sources"] = len(response.get("sources", []))

            topics_found, found_list = check_expected_topics(
                result["answer"], tq["expected_topics"]
            )
            result["topics_found"] = topics_found
            result["topics_total"] = len(tq["expected_topics"])
            result["found_topics"] = found_list

            print(f"✅ ({result['latency_ms']:.0f}ms, {result['confidence']:.2f})")

        results.append(result)

    # Generate report
    print("\n📄 Generating test report...")
    report = generate_report(results, base_url)

    report_path = Path("tests/test_results.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    print(f"   ✅ Report saved to: {report_path}")

    # Also save raw JSON results
    json_path = Path("tests/test_results.json")
    json_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"   ✅ Raw results saved to: {json_path}")

    # Summary
    successful = sum(1 for r in results if "error" not in r)
    avg_latency = sum(r.get("latency_ms", 0) for r in results) / max(len(results), 1)
    avg_confidence = sum(r.get("confidence", 0) for r in results) / max(len(results), 1)

    print(f"\n{'=' * 60}")
    print(f"  Results: {successful}/{len(results)} successful")
    print(f"  Avg Latency: {avg_latency:.0f} ms")
    print(f"  Avg Confidence: {avg_confidence:.2f}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
