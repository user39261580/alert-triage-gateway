import argparse
import json
import time
from pathlib import Path

import httpx

DEFAULT_MODELS = ["gpt-4o-mini", "gpt-5.4-nano", "gpt-5.4-mini"]
DEFAULT_ENDPOINT = "http://localhost:8000/api/v1/triage-alert"


def load_payloads(payload_file: Path) -> list[dict]:
    with payload_file.open("r", encoding="utf-8") as f:
        payloads = json.load(f)

    if not isinstance(payloads, list):
        raise ValueError("Payload file must contain a JSON array")

    return payloads


def run_comparison(endpoint: str, payloads: list[dict], models: list[str], timeout: float) -> list[dict]:
    results: list[dict] = []

    with httpx.Client(timeout=timeout) as client:
        for model in models:
            for payload in payloads:
                label = payload.get("label", "unlabeled")
                raw_log = payload.get("raw_log", "")
                expected = payload.get("expected_trust_score")

                request_payload = {
                    "raw_log": raw_log,
                    "model": model,
                }

                started = time.perf_counter()
                response = client.post(endpoint, json=request_payload)
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

                row: dict = {
                    "model": model,
                    "label": label,
                    "status_code": response.status_code,
                    "latency_ms": elapsed_ms,
                    "expected_trust_score": expected,
                }

                if response.status_code == 200:
                    body = response.json()
                    row.update(
                        {
                            "trust_score": body.get("trust_score"),
                            "service_valid": body.get("service_valid"),
                            "trace_id": body.get("langfuse_trace_id"),
                        }
                    )
                else:
                    row["error"] = response.text

                results.append(row)

    return results


def print_results(results: list[dict]) -> None:
    print("model,label,status_code,trust_score,expected_trust_score,service_valid,latency_ms,trace_id")
    for row in results:
        print(
            ",".join(
                [
                    str(row.get("model", "")),
                    str(row.get("label", "")),
                    str(row.get("status_code", "")),
                    str(row.get("trust_score", "")),
                    str(row.get("expected_trust_score", "")),
                    str(row.get("service_valid", "")),
                    str(row.get("latency_ms", "")),
                    str(row.get("trace_id", "")),
                ]
            )
        )


# Summaries make it easy to compare cost/latency/quality trends in Langfuse dashboards.
def print_summary(results: list[dict], models: list[str]) -> None:
    print("\nSummary")
    for model in models:
        subset = [r for r in results if r["model"] == model and r.get("status_code") == 200]
        if not subset:
            print(f"- {model}: no successful responses")
            continue

        avg_latency = round(sum(r["latency_ms"] for r in subset) / len(subset), 2)
        avg_trust = round(
            sum(float(r.get("trust_score") or 0.0) for r in subset) / len(subset),
            3,
        )
        print(f"- {model}: runs={len(subset)} avg_trust_score={avg_trust} avg_latency_ms={avg_latency}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run sample payloads across multiple LLM models.")
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"Triage endpoint URL (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--payload-file",
        default=str(Path(__file__).with_name("sample_payloads.json")),
        help="Path to sample payloads JSON file",
    )
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Model to include (repeat for multiple values). Defaults to 3-model lineup.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    models = args.models or DEFAULT_MODELS

    payloads = load_payloads(Path(args.payload_file))
    results = run_comparison(args.endpoint, payloads, models, args.timeout)

    print_results(results)
    print_summary(results, models)

    failures = [r for r in results if r.get("status_code") != 200]
    if failures:
        print(f"\nCompleted with {len(failures)} failed requests.")
        return 1

    print("\nCompleted successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
