# 0611 Hybrid Fusion Mode Comparison

Using the same 0605 sampled-task plan for all runs.

| Mode | Runs | Target Match Rate | Effectiveness Rate | Avg Wait (ms) | Min Wait (ms) | Max Wait (ms) | Activation Startup Modes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Hybrid (union) | 100 | 100.0% | 100.0% | 124.446 | 95.919 | 420.634 | running:100 |
| Hybrid (intersection) | 100 | 90.0% | 100.0% | 393.523 | 98.684 | 3385.384 | cold:10, running:90 |
| Hybrid (weighted) | 100 | 55.0% | 100.0% | 1308.378 | 90.544 | 6239.558 | cold:45, running:55 |
