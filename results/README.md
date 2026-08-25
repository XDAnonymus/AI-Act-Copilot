# Results

`evaluation.json` and `evaluation.md` contain the latest recorded 15-question functional evaluation.

The load-test artifacts are created by:

```powershell
python scripts/load_test.py --requests 50 --concurrency 1
```

That command writes `results/load_test.json` and `results/load_test.md` and updates the summary in the root README. The load test should be run on the same workstation/model setup used for the final demo because latency is hardware-dependent.
