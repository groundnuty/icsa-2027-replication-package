# Blind code inspection (#76, rubric amendment 11)

Runs the instrument labels `unknown` are resolved by two coders from different vendors reading the
code blind; a label changes only if both agree. The rubric is the science agent's
(`protocol/inspection-rubric.md` once amendment 11 is merged; its draft path until then, see
`rubric.py`). It is read at run time and its sha256 is recorded in every artifact; it is never copied here.

## Sequence

    # 1. population: one JSONL row per run (pilot, calibration, main, ktest); see queue.py. The campaign's runs, from its
    #    own records (K rows come from krun.py):
    python -m icsa.inspection.population --campaign-root ROOT [--pipeline-out DIR] --out population.jsonl
    # 2. packets + queue + key (the key stays OUTSIDE the packets dir; coders never see it)
    python -c "from icsa.inspection import queue; ..."            # queue.build(rows, seed=..., packets_dir=P, key_path=K, identifiers_for=...)
    # 3. the rubric's 10% cue reading: a fresh Sonnet reviewer reads a random 10% of P/*.txt for cues
    # 4. the coders (resumable; Codex one process at a time, Claude in a thread pool)
    python -m icsa.inspection.run --packets P --work W
    # 5. decisions, the report and the dossier artifact
    python -m icsa.inspection.report --key K --packets P --work W [--population POP] [--investigations I] \
        [--k-commit SHA] [--project pilot=N,main=M] --out OUT

## What each piece guarantees

- **population.py.** The rows `queue.build` takes, from the campaign store (the plan) and the pipeline's `run_labels.jsonl`,
  `scored_rows.jsonl` and `infra.json`:
  - one row per planned run, `run_key` the store key (a pilot and a main run of one cell share the record's key); the phase
    comes from the block, the label and `label_raw` as the pipeline wrote them (19(a) is already in it);
  - **unlabelled runs** (science, #76, 20:26Z and 22:28Z): a planned run with no final label (never started, pending, out of
    retries, not finished, a pipeline output missing or older than the store) is a row with `unlabelled: true` and `label: unknown`.
    It is never an R or C input and gets no coverage record; part 5 counts it as unknown, in its numerator and denominator.
    A run ended by the time cap is `time_capped: true` with NO label (None; "K" in report-spec, not set K), told by the scored row's
    termination and never by its `invalid_reason`; part 5 takes it out of both and reports it beside the share;
  - every other run (no phase, flagged out of the analysis, a bad flag, foreign to the store) is in `population.excluded.jsonl`
    with a reason; a labelled run whose directory lacks its packet's files, or has none recorded, stays a row, so `queue.build`
    refuses it into the key's `refused` and the report counts it (`--exclude-unbuildable` drops them, and part 5's denominator too);
  - which runs the coders see is still `queue.assign_sets`.
- **coverage.py.** The coders' coverage records for the analysis (`apply_inspection_coverage`): one per decided set R run, with
  `both_agree_exactly` (identical extractions, no CANNOT TELL) and the shares `1 - missing / required` per part from `compare`.
- **packet.py.** One text per run:
  - the prompt as the agent saw it (first user message of `transcript.json`);
  - the cells from `code_cells.json` paired with the transcript's python tool results (both
    transcript shapes; a mismatch refuses the packet), each stdout and stderr kept whole up to
    2,000 characters, else its first and last 1,000;
  - the files under `output/` with their sizes.
  - **Never included:** the final message, `report.json`'s content, the label, set, option or model
    as metadata.
  - **Sanitising:** identifiers (run key, scenario ids, model names, run dirs) become
    `RUN_/SCENARIO_/MODEL_/DIR_` tokens, consistently within a packet.
  - **Cue scan:** blocking cues refuse a packet; review cues are recorded for the 10% reading.
    Known-answer packets are built strict (any cue refuses).
  - **Ids:** the id is a keyed hash and is not in the text, so a run's text depends only on its content.
- **queue.py.** Assigns the sets:
  - **R:** every `unknown` run.
  - **C:** pilot and calibration decided runs; on main, a seeded 15 complete + 15 omitting per
    option × layout with the strata recorded, plus every `decoded_not_delivered` run, forced. **For the main block's coding plan** (`plan.build_report_key`)
    the sample is order-stable (science, #34, 4 Nov 18:53Z): a decided run joins C when a seeded hash of its run key (`queue.c_hash`) falls below
    its option × layout cell's rate, `plan.plan_c_rates` = the planned C size of the cell (2 × `c_main_per_cell`, the planned complete + omitting)
    over the plan's planned seed-1 runs there, at most 1. Membership depends on neither which runs have finished nor which were coded, so R and C can be
    coded as runs finish; the realised sizes are in the strata (`N`, `n`, `rate`, `expected`) and in the key's `c_rule`.
    The pagination cell (T-unpaginated) is phase `pagination` and follows main's rule: its `unknown` runs are R, its decided runs
    are sampled per option × layout (the rubric says "main runs" and does not name the cell).
  - **K:** the `ktest` rows.
  - **N:** every PILOT run with no label (time-capped or not): read like any packet, in the same order and text form, and its answer is
    never scored (no part, share, kappa, rate or coverage record reads it; a pending one makes nothing incomplete). One with no
    run directory or no code cell is refused into the key's `refused`, so every planned pilot run is in exactly one of R, C and N.
    Another phase's unlabelled runs stay in no set; the report counts them.

  The queue order is a seeded shuffle of the sorted ids. Refused packets are listed in the key, never dropped.
- **prompt.py.** Rubric §4 only, plus the answer schema (`answer.py`). Hashed; `run.py` refuses
  packets queued under another prompt hash.
- **coders.py / run.py.**
  - **Codex** `gpt-6-astra` (effort high, `-s read-only`, `--ephemeral --ignore-user-config`, an empty
    temporary cwd): any command, file, MCP or web event marks the attempt contaminated, and it is retried.
  - **Claude** `claude-opus-5-5`: adaptive thinking, effort high, json_schema output, the key read from
    `~/.secrets/icsa-2027/anthropic.key` at call time. No model fallback: a refusal is a
    failed attempt.
  - **Attempts:** up to 3 per packet and coder, every one archived, resumable. A malformed answer
    never becomes a verdict.
- **compare.py.** The §5 script against the instance's required extent (`icsa.instances`):
  - COMPLETE needs all of it covered with no CANNOT TELL anywhere;
  - a definite missing part gives OMITTING, even beside a CANNOT TELL;
  - otherwise CANNOT_TELL.

  It also hashes the exact missing cell-days and the whole canonical extraction.
- **decide.py.** An instrument `complete` or `omitting` stands. Only `unknown` is resolved: both
  COMPLETE gives complete, both OMITTING gives omitting, anything else stays unknown. The
  decomposition is computed only when both extractions agree exactly with no CANNOT TELL.
- **report.py.**
  - §7 parts 1–5. A part fails only if it fails with every unavailable evaluation taken
    favourably; it passes only if every evaluation is available.
  - Each coder's accuracy on K, the K and C pair error rates with Wilson intervals, and Cohen's
    kappa per option and per subject model.
  - The share resolved, tokens, time, cost and the projection.
  - Limitations and the replay-check status.
  - The dossier artifact `inspection_gate.json` (`icsa-inspection-gate-v1`).
- **krun.py.** Runs a known-answer case through the real harness (`execute_run`, a StubAdapter
  replaying its cells, the real sandbox, #9's tracer) and labels it with #9's labeller. Option M
  reads a hard-linked local copy at the real `/data/...` path (no site-g); T and D need site-g (`--allow-site-g`).

## The dependence test by replay (rubric §8; `replaycheck.py`, `replayrun.py`)
A report beside the labels, **not a go criterion**: it blocks nothing and changes no label. Positive evidence shows that some
values of a group are used, not that every required cell-day is; no change is never proof of omission, and no verdict that a run
omits anything exists in it.

    python -m icsa.inspection.replaycheck plan    --decisions D --population P --seed S --out OUT   # create or extend the plan
    python -m icsa.inspection.replaycheck run     --out OUT --scratch DIR --data-root DIR [--jobs N] [--limit N]
    python -m icsa.inspection.replaycheck summary --out OUT      # summary.json + replay_status.json (for report.py --replay-status)

- **Per run:** the recorded cells are replayed (no model, untraced) through the real harness and sandbox on the local simulation. The
  control (real data) must reproduce the run's own saved mask exactly, else the run is `not_replayable` and no perturbed arm runs.
  Then 4 groups (the reduced set: target, space, 2 seeded baseline years; `--groups all` is the rubric's 13), each on a copy of the data
  that differs in that one group by an additive offset (`--delta-k`) on the group's required sea cells. Outcomes per group:
  `positive`, `change_elsewhere`, `no_change`, `not_tested` (the reference did not move, or the arm failed).
- **Why space is not one offset:** the same offset on every day of a box cancels in the detector, so space is -delta on baseline days and
  +delta on target days. A baseline year is +delta only (a negative one moves the threshold about one rank). On an event-free instance
  no baseline group can move the reference.
- **The sample:** one fixed, ordered, append-only plan (`plan.json`): the pilot's resolved runs first (up to 4 per option, `complete`
  oversampled by `--complete-weight`), then the main block's, balanced per option x layout. Later arrivals are appended; nothing planned
  moves. Progress is a result file per run; `summary` says how far the work got, and what was not reached is a stated limitation.
- **Safety:** a hard-linked file is never opened for writing (S1: new files for the group's days, links for the rest; S2: a private full
  copy, deleted after the arm); every edited day is read back and compared bit for bit. A data configuration that is not the local mock
  is refused. Nothing in the code names a host: data root, scratch (on the data's filesystem, with room for an S2 copy), harness
  config, concurrency and caps are arguments.
- **A host to run it on** needs: Python 3.12 and `uv sync --frozen` of this checkout; Docker with the campaign image under its pinned id
  (`docker save` / `docker load`, then check the id); the daily S1 files, the S2 file and the site-g id index (`layout/ids.json`) in a data
  root; the harness config. It needs no published-fields file, no tracer, no model key and no route to site-g or site-f. Give the driver a hard
  memory cap, as `memcap` does where it exists: `systemd-run --user --scope -p MemoryMax=4G -p MemorySwapMax=0 -- python -m
  icsa.inspection.replaycheck run ...`. A small host: `--jobs 1 --max-sandboxes 1 --max-d 1 --max-s2-copies 1` and a `--min-free-gb`
  floor; each sandbox is also capped by `[sandbox_limits]` in the config. An arm that fails because the host did (no room, a sandbox
  failure in the control) makes the run an infra result, retried on the next invocation; it is never recorded as a finding.

## Known-answer cases (set K)
Written by the code agent, with answers fixed by construction in a local-only branch. The science agent
does not see them before the gate. Their commit is recorded (`--k-commit`) and a hash commitment is pushed
before the first coder call. No case is changed after any coder has seen it.

## The main block's coding plan (amendment 26, 29; `plan.py`)

    python -m icsa.inspection.plan build --campaign-root DIR --seed S --out plan.json [--stop-at 2026-11-06T06:00:00Z]
    python -m icsa.inspection.run --plan plan.json --work WORK --sealed SEALED [--input-root /mnt/volume2/icsa-2027/coding-mirror] \
        [--passes N --pass-interval-s S] [--codex-workers 6] [--max-packets N] [--notify-queue PATH] [--gate-wait-s 3600 --probe-s 600 --probe-slow-s 1800]
    python -m icsa.inspection.report --pair-plan plan.json --sealed SEALED --unseal --population POP --work WORK [--key GATE_KEY] --out OUT

- The seeded order over the planned matrix (Sonnet subject runs first, every prefix balanced per option x layout x model), written once with its
  seed, hash and coding stop; a second build must match byte for byte.
- B's runs: the coders read a merged store (`snapshot.bmerge stores`, the registered first-started-wins rule) whose B runs are recorded under their own mirrors; `--mirror-root` (repeatable) names each mirror's root, and a recorded path under a named root is read as it stands (a path under none is looked for below `--input-root`, as before, so an unnamed mirror's runs stay not finished instead of being guessed). The root is normalised (absolute, no `..`), a recorded path must stay inside it once links are followed (else the pass stops with an error), and none is under a `snapshot-mirror` directory. `--hold-keys FILE` (read afresh every pass) names runs that are not picked up yet: a run started on two providers waits for the merge to say which copy counts (science, #34 17:00Z).
- Passes over the fixed order while the block runs: a run is looked at for finished-or-not only (the store's status, the attempt's termination, the
  run directory's own `<dir>.pulled.json` marker, whose file count and bytes must match it: no marker, not finished); the coders code every finished run,
  never reading a label. Sets R and C are assigned at the report.
- The pair (Sol + Opus, or Opus + Sonnet) is recorded before any call and never changes; the 95% gate holds, waits, probes, switches (see `plan.py`).
- **The Sonnet-subject exception** (science, #34, 4 Nov 20:22Z): once the gate has closed AT THE THRESHOLD (95%), a Sonnet-subject run keeps using Sol (Sol + Opus; it never gets Opus + Sonnet) until the newest reading, a call's or a probe's, reaches the hard stop, 99% (`--sonnet-hard-stop`, `plan.SONNET_HARD_STOP_PERCENT`); every other run follows the 95% gate as before. No exception when the gate closed blind or on a limit error, after a limit error until a later answer reads under the hard stop, or on a blind streak. Past the hard stop nothing uses Sol, and the Sonnet-subject runs left are uncoded and counted in the report (`not_coded`; `sonnet_subject_sol_past_threshold` counts those coded under the exception; the gate's episode carries `sonnet_hard_stop_at`).
- Everything per packet is under the sealed directory; what is printed or written outside it is totals only.
- `report.py` and `coverage.py` take `--pair-plan` (a row per pair, no pooled rate, a Sol-only sensitivity row) and refuse a sealed directory
  without `--unseal`, which is the science agent's alone (amendment 29(c): an instruction, not a lock).
