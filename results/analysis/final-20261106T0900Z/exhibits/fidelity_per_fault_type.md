# snapshot final=true t=2026-11-06T09:00:00Z

# Fidelity per fault type

## whole files skipped (S1)

| option | layout | record | fault type | observable by design | tested | recall (95%) | precision (95%) | runs faulted / control |
|---|---|---|---|---|---|---|---|---|
| A | S1 | audit | whole_file_skip | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| A | S1 | traefik | whole_file_skip | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| D | S1 | audit | whole_file_skip | observable | yes | 1.00 (0.61–1.00) | 1.00 (0.61–1.00) | 6 / 29 |
| D | S1 | traefik | whole_file_skip | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| M | S1 | audit | whole_file_skip | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| M | S1 | perf | whole_file_skip | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |

## a run of whole files skipped (S1)

| option | layout | record | fault type | observable by design | tested | recall (95%) | precision (95%) | runs faulted / control |
|---|---|---|---|---|---|---|---|---|
| A | S1 | audit | file_range_skip | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| A | S1 | traefik | file_range_skip | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| D | S1 | audit | file_range_skip | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 29 |
| D | S1 | traefik | file_range_skip | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| M | S1 | audit | file_range_skip | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| M | S1 | perf | file_range_skip | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |

## chunks or time steps skipped (S2)

| option | layout | record | fault type | observable by design | tested | recall (95%) | precision (95%) | runs faulted / control |
|---|---|---|---|---|---|---|---|---|
| A | S2 | audit | chunk_range_skip | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| A | S2 | traefik | chunk_range_skip | observable per instance | per_instance | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| M | S2 | audit | chunk_range_skip | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S2 | perf | chunk_range_skip | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| A | S2 | audit | chunk_skip | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| A | S2 | traefik | chunk_skip | observable per instance | per_instance | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| M | S2 | audit | chunk_skip | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S2 | perf | chunk_skip | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |

## header-only reads (S1, S2)

| option | layout | record | fault type | observable by design | tested | recall (95%) | precision (95%) | runs faulted / control |
|---|---|---|---|---|---|---|---|---|
| A | S1 | audit | header_only | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 30 |
| A | S1 | traefik | header_only | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 30 |
| A | S2 | audit | header_only | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| A | S2 | traefik | header_only | observable per instance | per_instance | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| D | S1 | audit | header_only | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 29 |
| D | S1 | traefik | header_only | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 30 |
| D | S2 | audit | header_only | unobservable by design | no | 0.00 (0.00–0.16) | – | 20 / 30 |
| D | S2 | traefik | header_only | unobservable by design | no | 0.00 (0.00–0.16) | – | 20 / 30 |
| M | S1 | audit | header_only | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S1 | perf | header_only | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| M | S2 | audit | header_only | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S2 | perf | header_only | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |

## full read, partial use (S1, S2)

| option | layout | record | fault type | observable by design | tested | recall (95%) | precision (95%) | runs faulted / control |
|---|---|---|---|---|---|---|---|---|
| A | S1 | audit | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 30 |
| A | S1 | traefik | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 30 |
| A | S2 | audit | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| A | S2 | traefik | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| D | S1 | audit | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 29 |
| D | S1 | traefik | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 30 |
| D | S2 | audit | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.16) | – | 20 / 30 |
| D | S2 | traefik | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.16) | – | 20 / 30 |
| M | S1 | audit | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S1 | perf | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S2 | audit | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S2 | perf | full_read_partial_use | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |

## Other fault types (no paper row; the `all faults` rows and the other conditions are in the CSV)

| option | layout | record | fault type | observable by design | tested | recall (95%) | precision (95%) | runs faulted / control |
|---|---|---|---|---|---|---|---|---|
| A | S1 | audit | baseline_dropped | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| A | S1 | traefik | baseline_dropped | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| A | S2 | audit | baseline_dropped | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| A | S2 | traefik | baseline_dropped | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| D | S1 | audit | baseline_dropped | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 29 |
| D | S1 | traefik | baseline_dropped | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| M | S1 | audit | baseline_dropped | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| M | S1 | perf | baseline_dropped | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| M | S2 | audit | baseline_dropped | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S2 | perf | baseline_dropped | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| A | S1 | audit | target_dropped | observable | yes | 1.00 (0.61–1.00) | 1.00 (0.61–1.00) | 6 / 30 |
| A | S1 | traefik | target_dropped | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| A | S2 | audit | target_dropped | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| A | S2 | traefik | target_dropped | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| D | S1 | audit | target_dropped | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 29 |
| D | S1 | traefik | target_dropped | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| M | S1 | audit | target_dropped | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| M | S1 | perf | target_dropped | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| M | S2 | audit | target_dropped | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S2 | perf | target_dropped | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| A | S1 | audit | wrong_period | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| A | S1 | traefik | wrong_period | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| A | S2 | audit | wrong_period | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| A | S2 | traefik | wrong_period | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| D | S1 | audit | wrong_period | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 29 |
| D | S1 | traefik | wrong_period | observable | yes | 1.00 (0.65–1.00) | 1.00 (0.65–1.00) | 7 / 30 |
| M | S1 | audit | wrong_period | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| M | S1 | perf | wrong_period | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| M | S2 | audit | wrong_period | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S2 | perf | wrong_period | observable | yes | 1.00 (0.68–1.00) | 1.00 (0.68–1.00) | 8 / 30 |
| A | S1 | audit | wrong_region | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 30 |
| A | S1 | traefik | wrong_region | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 30 |
| A | S2 | audit | wrong_region | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| A | S2 | traefik | wrong_region | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| D | S1 | audit | wrong_region | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 29 |
| D | S1 | traefik | wrong_region | unobservable by design | no | 0.00 (0.00–0.35) | – | 7 / 30 |
| D | S2 | audit | wrong_region | unobservable by design | no | 0.00 (0.00–0.16) | – | 20 / 30 |
| D | S2 | traefik | wrong_region | unobservable by design | no | 0.00 (0.00–0.16) | – | 20 / 30 |
| M | S1 | audit | wrong_region | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S1 | perf | wrong_region | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S2 | audit | wrong_region | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |
| M | S2 | perf | wrong_region | unobservable by design | no | 0.00 (0.00–0.32) | – | 8 / 30 |

## Notes

How to read it. Source: `frozen/fault/h3_table.csv` (the registered H3 matrix); nothing here is recomputed. Condition `cold` only; the other conditions (M's warm_buffer, prefetch_on) and the `all faults` rows are in the CSV.
- **tested**: the fault type is in the tested subset of the cell (observable by design in that cell; `per_instance` = only the runs not masked by the client count). `no` = reported only.
  The cell's own H3 status (pass / fail / incomplete / not_testable) is `cell_status` in the CSV; per-type rows are never a verdict.
- **recall** is over every faulted run of the type, unobservable and masked ones included (the tested row of the cell is over the observable ones only), so a low recall where `tested` is `no` is by design.
- **precision** divides by the flags of the type's runs plus the WHOLE cell's control false alarms: one control alarm lowers every type's precision of that cell. The rows are not a partition.
- Intervals are Wilson 95%. A dash is undefined (no faulted run, or nothing flagged).
