# Evaluation and Performance Test

## Functional evaluation

The evaluation set contains 15 curated questions in `data/eval/questions.json`. It covers scope and definitions, high-risk classification, obligations, transparency, application dates, prohibited practices, a Hungarian query, and one out-of-scope request.

Run:

```powershell
python scripts/evaluate.py
```

The script writes `results/evaluation.json` and `results/evaluation.md` and refreshes the summary in the root README.

### Automated metrics

- **Intent accuracy:** expected vs. actual router intent.
- **Retrieval hit rate:** whether at least one configured expected legal marker is found in retrieved evidence. Questions without retrieval markers are excluded from this denominator. This is a lightweight regression metric and can overestimate retrieval completeness.
- **Citation presence rate:** citations found in the generated draft before the final source appendix is added. Out-of-scope questions are excluded.
- **Verification pass rate:** deterministic evidence/citation-structure gate for in-scope questions; it does not measure semantic entailment or legal correctness.
- **Latency:** mean, p50 and p95 end-to-end latency.

The current recorded run is summarized in `results/evaluation.md`, including the failed cases. These metrics are useful for regression testing, but they are not a legal-correctness score.

## Load scenario

Run 50 requests for the baseline scenario:

```powershell
python scripts/load_test.py --requests 50 --concurrency 1
```

The script accepts 50-200 requests. On a stronger workstation, a concurrent run can also be useful:

```powershell
python scripts/load_test.py --requests 50 --concurrency 2
```

It writes `results/load_test.json` and `results/load_test.md` with latency percentiles, throughput, success/error counts, mean latency by LangGraph node, the measured slowest node, and optimization suggestions.

Do not name a bottleneck before measuring it. With a large local generation model, `classify` or `answer` is a plausible candidate, but the report should be based on node timings from the actual workstation.

## Manual review

For the recorded functional run, the two automated failures are the most useful manual-review cases:

- **E10:** the final answer contained the general application date from the deterministic date tool, but retrieval missed the expected Article 113/date marker. This indicates a grounding/retrieval gap for a timeline query.
- **E15:** the user-facing response correctly rejected the weather question as out of scope, while the internal intent label was `general_research`. This is a state-label consistency issue rather than a bad final response.

For a final submission, also spot-check at least one clean retrieval case and one high-risk classification case against the cited source text.
