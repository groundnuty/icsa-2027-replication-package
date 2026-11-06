# snapshot final=true t=2026-11-06T09:00:00Z

Coder pairs (amendment 26(j)), over the 2428 primary-scope run(s) the analysis selects, not this table's own runs: no inspection input, so no run has a pair

| option | layout | record | condition | subset | tested | n_faulted | n_detected | n_control | n_false_alarm | n_false_flag_faulted | n_true_and_false_flag | n_false_flag_unobservable | recall | recall_lo | recall_hi | precision | precision_lo | precision_hi | false_alarm | false_alarm_lo | false_alarm_hi | status | meets_h3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D | S1 | audit | cold | all | False | 55 | 34 | 29 | 0 | 0 | 0 | 0 | 0.6182 | 0.4861 | 0.7348 | 1 | 0.8985 | 1 | 0 | -1.388e-17 | 0.117 | reported | nan |
| D | S1 | audit | cold | observable | True | 34 | 34 | 29 | 0 | 0 | 0 | 0 | 1 | 0.8985 | 1 | 1 | 0.8985 | 1 | 0 | -1.388e-17 | 0.117 | incomplete | nan |
| D | S1 | traefik | cold | all | False | 56 | 35 | 30 | 0 | 0 | 0 | 0 | 0.625 | 0.4941 | 0.7399 | 1 | 0.9011 | 1 | 0 | 0 | 0.1135 | reported | nan |
| D | S1 | traefik | cold | observable | True | 35 | 35 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9011 | 1 | 1 | 0.9011 | 1 | 0 | 0 | 0.1135 | incomplete | nan |
| D | S2 | audit | cold | all | False | 60 | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0.06017 | nan | nan | nan | 0 | 0 | 0.1135 | reported | nan |
| D | S2 | audit | cold | observable | True | 0 | 0 | 30 | 0 | 0 | 0 | 0 | nan | nan | nan | nan | nan | nan | 0 | 0 | 0.1135 | not_testable | nan |
| D | S2 | traefik | cold | all | False | 60 | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0.06017 | nan | nan | nan | 0 | 0 | 0.1135 | reported | nan |
| D | S2 | traefik | cold | observable | True | 0 | 0 | 30 | 0 | 0 | 0 | 0 | nan | nan | nan | nan | nan | nan | 0 | 0 | 0.1135 | not_testable | nan |
| M | S1 | audit | cold | all | False | 64 | 40 | 30 | 0 | 0 | 0 | 0 | 0.625 | 0.5025 | 0.7333 | 1 | 0.9124 | 1 | 0 | 0 | 0.1135 | reported | nan |
| M | S1 | audit | cold | observable | True | 40 | 40 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9124 | 1 | 1 | 0.9124 | 1 | 0 | 0 | 0.1135 | pass | True |
| M | S1 | audit | prefetch_on | all | False | 64 | 40 | 30 | 0 | 0 | 0 | 0 | 0.625 | 0.5025 | 0.7333 | 1 | 0.9124 | 1 | 0 | 0 | 0.1135 | reported | nan |
| M | S1 | audit | prefetch_on | observable | True | 40 | 40 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9124 | 1 | 1 | 0.9124 | 1 | 0 | 0 | 0.1135 | pass | True |
| M | S1 | audit | warm_buffer | all | False | 64 | 40 | 30 | 0 | 0 | 0 | 0 | 0.625 | 0.5025 | 0.7333 | 1 | 0.9124 | 1 | 0 | 0 | 0.1135 | reported | nan |
| M | S1 | audit | warm_buffer | observable | True | 40 | 40 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9124 | 1 | 1 | 0.9124 | 1 | 0 | 0 | 0.1135 | pass | True |
| M | S1 | perf | cold | all | False | 64 | 48 | 30 | 0 | 0 | 0 | 0 | 0.75 | 0.6318 | 0.8399 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | reported | nan |
| M | S1 | perf | cold | observable | True | 48 | 48 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9259 | 1 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | pass | True |
| M | S1 | perf | prefetch_on | all | False | 64 | 48 | 30 | 0 | 0 | 0 | 0 | 0.75 | 0.6318 | 0.8399 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | reported | nan |
| M | S1 | perf | prefetch_on | observable | True | 48 | 48 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9259 | 1 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | pass | True |
| M | S1 | perf | warm_buffer | all | False | 64 | 48 | 30 | 0 | 0 | 0 | 0 | 0.75 | 0.6318 | 0.8399 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | reported | nan |
| M | S1 | perf | warm_buffer | observable | True | 48 | 48 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9259 | 1 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | pass | True |
| M | S2 | audit | cold | all | False | 64 | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0.05662 | nan | nan | nan | 0 | 0 | 0.1135 | reported | nan |
| M | S2 | audit | cold | observable | True | 0 | 0 | 30 | 0 | 0 | 0 | 0 | nan | nan | nan | nan | nan | nan | 0 | 0 | 0.1135 | not_testable | nan |
| M | S2 | audit | prefetch_on | all | False | 64 | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0.05662 | nan | nan | nan | 0 | 0 | 0.1135 | reported | nan |
| M | S2 | audit | prefetch_on | observable | True | 0 | 0 | 30 | 0 | 0 | 0 | 0 | nan | nan | nan | nan | nan | nan | 0 | 0 | 0.1135 | not_testable | nan |
| M | S2 | audit | warm_buffer | all | False | 64 | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0.05662 | nan | nan | nan | 0 | 0 | 0.1135 | reported | nan |
| M | S2 | audit | warm_buffer | observable | True | 0 | 0 | 30 | 0 | 0 | 0 | 0 | nan | nan | nan | nan | nan | nan | 0 | 0 | 0.1135 | not_testable | nan |
| M | S2 | perf | cold | all | False | 64 | 48 | 30 | 0 | 0 | 0 | 0 | 0.75 | 0.6318 | 0.8399 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | reported | nan |
| M | S2 | perf | cold | observable | True | 48 | 48 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9259 | 1 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | pass | True |
| M | S2 | perf | prefetch_on | all | False | 64 | 48 | 30 | 0 | 0 | 0 | 0 | 0.75 | 0.6318 | 0.8399 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | reported | nan |
| M | S2 | perf | prefetch_on | observable | True | 48 | 48 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9259 | 1 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | pass | True |
| M | S2 | perf | warm_buffer | all | False | 64 | 48 | 30 | 0 | 0 | 0 | 0 | 0.75 | 0.6318 | 0.8399 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | reported | nan |
| M | S2 | perf | warm_buffer | observable | True | 48 | 48 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9259 | 1 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | pass | True |
| T | S1 | audit | cold | all | False | 55 | 34 | 30 | 0 | 0 | 0 | 0 | 0.6182 | 0.4861 | 0.7348 | 1 | 0.8985 | 1 | 0 | 0 | 0.1135 | reported | nan |
| T | S1 | audit | cold | observable | True | 34 | 34 | 30 | 0 | 0 | 0 | 0 | 1 | 0.8985 | 1 | 1 | 0.8985 | 1 | 0 | 0 | 0.1135 | incomplete | nan |
| T | S1 | traefik | cold | all | False | 56 | 35 | 30 | 0 | 0 | 0 | 0 | 0.625 | 0.4941 | 0.7399 | 1 | 0.9011 | 1 | 0 | 0 | 0.1135 | reported | nan |
| T | S1 | traefik | cold | observable | True | 35 | 35 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9011 | 1 | 1 | 0.9011 | 1 | 0 | 0 | 0.1135 | incomplete | nan |
| T | S2 | audit | cold | all | False | 64 | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0.05662 | nan | nan | nan | 0 | 0 | 0.1135 | reported | nan |
| T | S2 | audit | cold | observable | True | 0 | 0 | 30 | 0 | 0 | 0 | 0 | nan | nan | nan | nan | nan | nan | 0 | 0 | 0.1135 | not_testable | nan |
| T | S2 | traefik | cold | all | False | 64 | 48 | 30 | 0 | 0 | 0 | 0 | 0.75 | 0.6318 | 0.8399 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | reported | nan |
| T | S2 | traefik | cold | observable | True | 48 | 48 | 30 | 0 | 0 | 0 | 0 | 1 | 0.9259 | 1 | 1 | 0.9259 | 1 | 0 | 0 | 0.1135 | pass | True |
