# 0611 All Mode Comparison

Keyword/Semantic versus three Hybrid fusion modes on the same sampled-task set.

| Mode | Runs | Target Match Rate | Effectiveness Rate | Avg Wait (ms) | Min Wait (ms) | Max Wait (ms) | Activation Startup Modes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Keyword Only | 100 | 90.0% | 100.0% | 323.021 | 117.452 | 2878.706 | cold:10, running:90 |
| Semantic Only | 100 | 100.0% | 100.0% | 131.594 | 115.546 | 244.818 | running:100 |
| Hybrid (union) | 100 | 100.0% | 100.0% | 124.446 | 95.919 | 420.634 | running:100 |
| Hybrid (intersection) | 100 | 90.0% | 100.0% | 393.523 | 98.684 | 3385.384 | cold:10, running:90 |
| Hybrid (weighted) | 100 | 55.0% | 100.0% | 1308.378 | 90.544 | 6239.558 | cold:45, running:55 |
