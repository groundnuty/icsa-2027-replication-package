# Blind inspection: gate report

Overall status: **incomplete**

- rubric: /mnt/volume2/icsa-2027/wt/lk-pk3/protocol/inspection-rubric.md sha256 50e91fa231731a29a04842fb5ee933b456cc479d85b5a063936079a858efc8ac
- prompt sha256: 723bd916225aae89bd090104df037a21e04ce52f40f7f74afb11ed4385a3a823
- K set committed at: None
- packets: {'K': 81}
- refused packets: 0
- pending packets: 81
- problems: 0


## Go criterion 3 (rubric 7)

| part | status |
|---|---|
| 1 K, pair against truth | incomplete |
| 2 K, full procedure | incomplete |
| 3 K by option | incomplete |
| 4 set C pilot | incomplete |
| 5 pilot unknown share | incomplete |

### Part 1
- omitting cases answered COMPLETE by both: 0/41 (must be 0)
- complete cases answered COMPLETE by both: 0/40 = 0.0% (at least 80%)
- complete cases answered OMITTING by both: 0/40 (must be 0)

### Part 2
- omitting cases ending complete: 0/41 (must be 0)

### Part 3 (by option, option-matched subset)
- T: incomplete (n=11); part 1 incomplete, part 2 incomplete
- D: incomplete (n=12); part 1 incomplete, part 2 incomplete
- M: incomplete (n=8); part 1 incomplete, part 2 incomplete

### Part 4 (set C, pilot and calibration)
- COMPLETE by both while instrument omitting: 0/0 (must be 0)
- OMITTING by both while instrument complete: 0/0 (at most 10%)
- disagreements: 0; pending investigation: 0

### Part 5 (pilot runs unknown after inspection)
- unknown: 0/0 = n/a (at most 10%); basis: keyed runs only (no population given): the denominator is the keyed pilot runs
- of the planned runs counted, unlabelled (not finished or not started; counted unknown, never inspected): 0
- calibration (information only): 0/0

## Each coder on K
- codex: correct 0/81, wrong 0, cannot tell 0, malformed 0, pending 81
  - option D: correct 0 of 12, wrong 0 (95% upper bound n/a), not correct 0 (95% upper bound n/a), pending 12
  - option M: correct 0 of 58, wrong 0 (95% upper bound n/a), not correct 0 (95% upper bound n/a), pending 58
  - option T: correct 0 of 11, wrong 0 (95% upper bound n/a), not correct 0 (95% upper bound n/a), pending 11
- claude: correct 81/81, wrong 0, cannot tell 0, malformed 0, pending 0
  - option D: correct 12 of 12, wrong 0 (95% upper bound 26.5%), not correct 0 (95% upper bound 26.5%), pending 0
  - option M: correct 58 of 58, wrong 0 (95% upper bound 6.2%), not correct 0 (95% upper bound 6.2%), pending 0
  - option T: correct 11 of 11, wrong 0 (95% upper bound 28.5%), not correct 0 (95% upper bound 28.5%), pending 0
  - 2 omitting case(s) where claude names more parts than the truth; as registered, the coders' coverage comes only from extractions that agree exactly, so a difference between the coders leaves it null
- The upper bounds are exact (Clopper-Pearson, two-sided 95%): a perfect score on few cases bounds little, so set C (real, instrument-decided runs) weighs more where an option has few K cases (science, #76, 20:12Z).

## K with and without omitting cases that state the narrowing (descriptive, not part of the gate)
Omitting cases that openly say less data is used: 28 of 41 = 68.3%; core: 13 of 26, option-matched: 15 of 15.
- codex: all cases correct 0/81, without them 0/53; omitting cases correct 0/41, without them 0/13
- claude: all cases correct 81/81, without them 53/53; omitting cases correct 41/41, without them 13/13

## Cohen's kappa between the coders
categories COMPLETE/OMITTING/CANNOT_TELL; MALFORMED counted as CANNOT_TELL; real runs = sets R and C; pending packets excluded

| group | n | kappa | observed | expected |
|---|---|---|---|---|
| real overall | 0 | null (no packets) | n/a | n/a |
| K | 0 | null (no packets) | n/a | n/a |

## Coder pair against truth on K (Wilson 95%)
- overall: false-complete 0/0 [n/a, n/a]; false-omitting 0/0 [n/a, n/a]
- option D: false-complete 0/0 [n/a, n/a]; false-omitting 0/0 [n/a, n/a]
- option M: false-complete 0/0 [n/a, n/a]; false-omitting 0/0 [n/a, n/a]
- option T: false-complete 0/0 [n/a, n/a]; false-omitting 0/0 [n/a, n/a]

## Share resolved (set R)
- overall: 0/0 (pending 0, refused 0, counted unresolved)

## Coder pair on set C (Wilson 95%)
- pilot_and_calibration_raw
- main_raw
- pilot_and_calibration_by_model
- main_by_model
- main_reweighted: {"false_complete": {"est_k": 0, "N": 0, "rate": null}, "false_omitting": {"est_k": 0, "N": 0, "rate": null}}

## Route mix
{"omitted": "no population given: the route mix needs every run, not only the queued ones"}

## Subagents
- claude K: 0/81 packets with a subagent (0.0%); not recorded 0
- claude all: 0/81 packets with a subagent (0.0%); not recorded 0

## Tokens, wall time, cost
- claude K: n=81 tokens={'input_tokens': 1100424, 'cached_input_tokens': 0, 'output_tokens': 204943, 'reasoning_tokens': 0} wall={'total': 2060.409, 'mean': 25.437148148148147, 'median': 24.006, 'n': 81} cost={'total': 8.500556, 'mean': 0.10494513580246914, 'median': 0.103252, 'n': 81, 'n_null': 0} attempts=81 retried=0 contaminated=0
- claude all: n=81 tokens={'input_tokens': 1100424, 'cached_input_tokens': 0, 'output_tokens': 204943, 'reasoning_tokens': 0} wall={'total': 2060.409, 'mean': 25.437148148148147, 'median': 24.006, 'n': 81} cost={'total': 8.500556, 'mean': 0.10494513580246914, 'median': 0.103252, 'n': 81, 'n_null': 0} attempts=81 retried=0 contaminated=0

### Tokens and cost per option (real runs)

### Tokens and cost per subject model (real runs)

## Independent check
- not built: the replay dependence test (rubric §8) is built during the campaign; until then this is a stated limitation

## Stated limitations
- models judging model-written code
- coders cannot be blind to the option
- set C skews towards vectorised code, so it measures the coders on the easier part of the population
- the extraction relies on reading code, not executing it
- Claude Opus 5.5 shares a vendor with two subject models (Claude Haiku 5.5, Claude Sonnet 5.5); agreement is reported per subject model
