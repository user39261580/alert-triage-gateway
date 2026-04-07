import os
import httpx
import json
import sys
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Using port 8000 as the app is mapped to it
BASE_URL = os.getenv("CLOUD_BASE_URL", "")
API_URL = f"{BASE_URL}/api/v1"

def test_health():
    print(f"Checking health at {BASE_URL}/health...")
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=10.0)
        print(f"Status: {response.status_code}")
        print(f"Body: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def run_triage_tests():
    print(f"\nRunning triage tests against {API_URL}/triage-alert...")
    try:
        with open("tests/sample_payloads.json", "r") as f:
            payloads = json.load(f)
    except FileNotFoundError:
        print("Error: tests/sample_payloads.json not found.")
        return False

    success_count = 0
    for payload in payloads:
        label = payload.get("label", "unknown")
        raw_log = payload.get("raw_log", "")
        print(f"\nTesting: {label}")
        print(f"Log: {raw_log[:50]}...")
        
        try:
            # Explicitly include raw_log in payload
            response = httpx.post(f"{API_URL}/triage-alert", json={"raw_log": raw_log}, timeout=15.0)
            if response.status_code == 200:
                body = response.json()
                print(f"SUCCESS: {response.status_code}")
                print(f"Trust Score: {body.get('trust_score')}")
                print(f"Service Valid: {body.get('service_valid')}")
                # print(f"Triage: {body.get('triage')}")
                # print(f"Trace ID: {body.get('langfuse_trace_id')}")
                success_count += 1
            else:
                print(f"FAILED: {response.status_code}")
                print(f"Body: {response.text}")
        except Exception as e:
            print(f"Error during request: {e}")

    print(f"\nSummary: {success_count}/{len(payloads)} tests passed.")
    return success_count == len(payloads)

if __name__ == "__main__":
    health_ok = test_health()
    if not health_ok:
        print("Health check failed, aborting tests.")
        sys.exit(1)
    
    all_ok = run_triage_tests()
    if not all_ok:
        sys.exit(1)
    sys.exit(0)
