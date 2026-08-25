import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter

from app.agent_graph import build_agent_graph
from app.config import BASE_DIR
from app.retrieval import Retriever
from reporting import update_readme_section


RESULT_JSON = BASE_DIR / "results" / "load_test.json"
RESULT_MD = BASE_DIR / "results" / "load_test.md"
DATASET = BASE_DIR / "data" / "eval" / "questions.json"


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * p))
    return ordered[index]


def run_one(graph, question: str) -> dict:
    started = perf_counter()
    result = graph.invoke(
        {
            "question": question,
            "as_of": "2026-08-24",
            "retry_count": 0,
            "trace": [],
        }
    )
    return {
        "latency_ms": (perf_counter() - started) * 1000,
        "trace": result.get("trace", []),
        "ok": bool(result.get("final_answer")),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=1)
    args = parser.parse_args()

    if not 50 <= args.requests <= 200:
        raise SystemExit("--requests must be between 50 and 200 for the assignment scenario")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be at least 1")

    questions = json.loads(DATASET.read_text(encoding="utf-8"))
    sequence = [questions[index % len(questions)]["question"] for index in range(args.requests)]

    results = []
    wall_started = perf_counter()
    with Retriever() as retriever:
        graph = build_agent_graph(retriever)

        if args.concurrency == 1:
            for index, question in enumerate(sequence, start=1):
                result = run_one(graph, question)
                results.append(result)
                print(f"{index}/{args.requests}: {result['latency_ms']:.0f} ms")
        else:
            with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
                futures = [executor.submit(run_one, graph, question) for question in sequence]
                for index, future in enumerate(as_completed(futures), start=1):
                    result = future.result()
                    results.append(result)
                    print(f"{index}/{args.requests}: {result['latency_ms']:.0f} ms")

    wall_seconds = perf_counter() - wall_started

    latencies = [result["latency_ms"] for result in results]
    node_timings: dict[str, list[float]] = {}
    for result in results:
        for entry in result["trace"]:
            node_timings.setdefault(entry["node"], []).append(float(entry["duration_ms"]))

    node_means = {
        node: round(statistics.mean(values), 2)
        for node, values in node_timings.items()
        if values
    }
    bottleneck = max(node_means, key=node_means.get) if node_means else "unknown"

    if bottleneck == "answer":
        optimizations = [
        "Use a smaller or quantized local model for final answer synthesis, or reduce the maximum generated response length.",
        "Reduce MAX_EVIDENCE / the amount of retrieved context passed to the answer node after validating retrieval quality.",
    ]
    elif bottleneck == "classify":
        optimizations = [
        "Use a smaller local model for routing/classification.",
        "Cache repeated classification inputs during evaluation or repeated workloads.",
    ]
    elif bottleneck == "research":
        optimizations = [
            "Reduce retrieval_top_k/max_evidence after validating recall on the evaluation set.",
            "Cache query embeddings and repeated retrieval results.",
        ]
    else:
        optimizations = [
            "Profile the slowest node in isolation and reduce work performed per request.",
            "Cache deterministic/repeated work where the input corpus is unchanged.",
        ]

    summary = {
        "requests": args.requests,
        "concurrency": args.concurrency,
        "successful": sum(result["ok"] for result in results),
        "errors": sum(not result["ok"] for result in results),
        "wall_seconds": round(wall_seconds, 2),
        "throughput_requests_per_second": round(args.requests / wall_seconds, 3),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2),
            "p50": round(percentile(latencies, 0.50), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "p99": round(percentile(latencies, 0.99), 2),
        },
        "node_mean_latency_ms": node_means,
        "bottleneck": bottleneck,
        "optimization_suggestions": optimizations,
    }

    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    node_rows = "\n".join(f"| {node} | {value:.0f} ms |" for node, value in sorted(node_means.items()))
    optimization_rows = "\n".join(f"- {item}" for item in optimizations)
    markdown = f"""# Load Test Results

Generated by `python scripts/load_test.py --requests {args.requests} --concurrency {args.concurrency}`.

| Metric | Result |
|---|---:|
| Requests | {summary['requests']} |
| Concurrency | {summary['concurrency']} |
| Successful | {summary['successful']} |
| Errors | {summary['errors']} |
| Throughput | {summary['throughput_requests_per_second']:.3f} req/s |
| Mean latency | {summary['latency_ms']['mean']:.0f} ms |
| p50 latency | {summary['latency_ms']['p50']:.0f} ms |
| p95 latency | {summary['latency_ms']['p95']:.0f} ms |
| p99 latency | {summary['latency_ms']['p99']:.0f} ms |

## Mean Node Latency

| Node | Mean |
|---|---:|
{node_rows}

## Main Bottleneck

`{bottleneck}`

## Optimization Suggestions

{optimization_rows}
"""
    RESULT_MD.write_text(markdown, encoding="utf-8")
    readme_summary = f"""| Metric | Result |
|---|---:|
| Requests | {summary['requests']} |
| Concurrency | {summary['concurrency']} |
| Errors | {summary['errors']} |
| p50 latency | {summary['latency_ms']['p50']:.0f} ms |
| p95 latency | {summary['latency_ms']['p95']:.0f} ms |
| p99 latency | {summary['latency_ms']['p99']:.0f} ms |
| Bottleneck | `{summary['bottleneck']}` |

Full report: `results/load_test.md`."""
    update_readme_section(
        BASE_DIR / "README.md",
        "<!-- LOAD_RESULTS_START -->",
        "<!-- LOAD_RESULTS_END -->",
        readme_summary,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
