# Interim snapshots (#34)

A snapshot at time `t` covers the runs first started by `t - cap` (counted start: the first started attempt or the deferral; a retry never moves it).
Each is done as of `t`, exhausted as of `t`, or unfinished (not waited for; see below for how the analysis counts it). Runs that started later are out, finished or not.
**The paper's analysis (amendment 29(c), its time moved by amendment 43(a)) is one fixed snapshot: `--t 2026-11-06T09:00:00Z`, `--cap-s` = the final time cap, `--no-outcome as-exhausted`, `--final true`**, with
coding of those runs stopped at 09:30Z (a label not coded by then stays `unknown`). `--no-outcome` is required, no default. `as-exhausted` turns every in-cut run
with no outcome at `t` into an exhausted run in the store copy, before the unchanged pipeline and analysis run, so it leaves the primary denominators, is reported
per cell and counts as time-capped and a failure in the sensitivity row. The converted run keys are written to the copy's meta `snapshot_no_outcome_runs`, so
`exhausted_per_cell` splits `n_infrastructure` from `n_no_outcome_at_snapshot`. `report` (earlier, descriptive parts) leaves them `unfinished`, in the cohort (the cut stamps
`cohort_cut_utc` at `t - cap` plus a second), and "never imputed" holds for that case and for the primary analysis in both. Earlier parts carry no claims: Holm decisions
and smallest-effect verdicts are read only from the fixed snapshot.
`--final {true,false}` is required, no default. **`--final true` is accepted only on the fixed cut** (the instant 2026-11-06T09:00:00Z, however spelled, with
`--no-outcome as-exhausted`; the two values are `FINAL_T` and `FINAL_NO_OUTCOME` in `snapshot/cut.py`), and is refused (exit 2, nothing made) for any other `--t` or `--no-outcome`;
on the `analyse` stage it is checked again against the cut that was made (`cut.json`). `--final false` is accepted for any cut, a rehearsal of the fixed cut included.
`final` is in `SNAPSHOT.json` (true/false), and **the first line of every table under `OUT/tables/` (each `.csv` and `.md`) is `# snapshot final=<true|false> t=<t>`**.
Read a CSV with `pd.read_csv(path, skiprows=1)`; do not use `comment='#'` (it cuts an unquoted cell at its first #). A Markdown table has the line as a heading and a blank line after it. A table with no columns at all (an empty frame; `mixed_fixed_effects.csv` is one on the test campaign) is the line and a blank line: pandas raises `EmptyDataError` on it, as it does on the same file without the line.
`manifest.json` and the `fig_*.png` figures are not tables and carry no line; any other kind of file in `tables/` stops the run with an error, as does a table without the line.
Partial populations are analysed as they are (science's ruling, #34): the tables carry `n_regions` and `n_regions_dropped` per contrast.
This is instruction, not a lock: every session here is one user. Run it from your own session; no lane computes a contrast.

## Run it (from the repository root, at the frozen commit; Python as the repository's venv)

    OUT=<an ignored, untracked path in your workspace>/snap-<n>        # must not exist or be empty; a tracked path is refused

    # 1. the cut: copies the campaign's store (read-only), writes OUT/work/cut/{state.sqlite,run_dirs.txt,cut.json}
    python -m snapshot cut --campaign-root <campaign root on this host or its copy> --t <ISO UTC, not in the future> --cap-s <the main block's cap, seconds> \
 --no-outcome <report|as-exhausted> --final <true|false> --out $OUT --overhead <file|none> --fidelity-rows <file|none> --inspection-labels <file|none>

    # 2. (not needed after snapshot.fetch) the runs' directories from the run host (rsync, ionice idle, nice 19, bandwidth limit required, no delete); recorded in OUT/work/pull.json
    python -m snapshot.pull --out $OUT --src-host email-1@example --bwlimit-kib 20000 --dest-root / --min-free-gib 20 \
        --ssh "ssh -o BatchMode=yes -o IdentitiesOnly=yes -i ~/.secrets/icsa-2027/runvm_ed25519 -o UserKnownHostsFile=~/.secrets/icsa-2027/runvm_known_hosts"
    # (prefix with SSH_AUTH_SOCK= if ssh hangs.) The pull is the only step that writes outside OUT. It writes ONLY the run directories listed in
    # OUT/work/cut/run_dirs.txt, each at its recorded absolute path below --dest-root (required, no default; `/` on the host that runs the analysis,
    # because the store records absolute paths), updating in place and never deleting, plus OUT/work/pull.json. It refuses when --dest-root is not a
    # directory, or when the filesystem each run directory lands on has under --min-free-gib (default 20) GiB free. Free space on this host now: about 123 GB on
    # /mnt/volume2 and about 17 GB on /, and the store records /mnt/volume2 paths, so the check reads /mnt/volume2. Check the cut's size first.

    # 3. the pipeline and the analysis on the cut (CPU and memory heavy: cap it; never on the run host)
    python -m snapshot analyse --campaign-root <same> --t <same> --cap-s <same> --no-outcome <same> --final <same> --out $OUT --overhead ... --fidelity-rows ... --inspection-labels ... --jobs 2

`run` does steps 1 and 3 in one call (the directories must already be in place). `analyse` accepts an `OUT` that holds the cut of a `cut` stage and nothing of an analysis (it was refused before). `--t`, `--cap-s`, `--no-outcome` and `--final` have no default; `none` states "not measured / not run".
Give `--index-root`, `--data-dir`, `--s1-dir` and `--mount-root` as `python -m icsa.pipeline` does.

## Fetching without ssh afterwards: `snapshot.fetch` (the lead runs it, into one directory, again and again)

    python -m snapshot.fetch --src-host email-1@example --ssh "<the ssh command, as rsync -e takes it>" --campaign-root <the campaign root ON THE RUN HOST> \
        --dest D --bwlimit-kib 20000 [--min-free-gib 20] [--src-tmp-dir /tmp] [--src-min-free-gib 1]

- **On the run host:** a consistent copy of `R/state.sqlite` (`VACUUM INTO` over a read-only connection; a store with no -wal/-shm is copied as bytes, since a read-only open would
  create them) into `<src-tmp-dir>/icsa-snapshot-fetch-<time>-<random>.sqlite`: outside R's tree (refused if inside), after a free-space check (2 x the store plus `--src-min-free-gib`),
  never over an existing file. Nothing is written in R. Only that temporary file is removed, once the copy is here and checked (sha256 against the source's, `integrity_check`).
  **On any failure the temporary copy's path is printed with whether it was removed**; on success nothing about it (unless the removal itself failed: then a warning names the path). A fetch killed by SIGKILL can leave one:
  `ls <src-tmp-dir>/icsa-snapshot-fetch-*` on the run host (SIGTERM and Ctrl-C clean up; a hung ssh or rsync is killed after `--timeout-s`).
- **D** is created mode 700 and refused if it exists broader than 700, is not ours, or is non-empty and not a previous fetch's (`D/.fetch/layout.json`). It is the same
  directory every time. It holds `state.sqlite`, `fetch.json` (the last fetch's counts), `.fetch/` (work files) and the run directories at their recorded absolute paths below D.
- **Run directories, one rsync each** (the same command as `snapshot.pull`: ionice idle, nice 19, `--bwlimit-kib` required, no delete, recursive, the disk floor `--min-free-gib` checked before each).
  Only the finished runs' (a done attempt of a done run) directories are read from the new store copy: paths, attempt ids and end times, never a label, a token count or content.
  When rsync exits 0 for a directory, `<run_dir>.pulled.json` is written beside it by atomic rename: its file count and bytes and the attempt it is for. **A directory with a valid marker is
  skipped.** A marker is valid only if the store copy still lists that same path for the same attempt (id and end time) and the directory still has the marker's file count and bytes;
  otherwise the marker is deleted first and the directory pulled again. A failed or killed rsync leaves no marker and is retried next time. Run directories are per attempt
  (`attempt<N>.try<M>`, M counts the run's attempts, so a path is never reused), so a finished attempt's directory does not change on the source, and a run re-queued after an
  error gets a new directory: the old attempt's marker is left beside its old directory and nothing reads it, since the store no longer calls that attempt finished.
- **`D/state.sqlite`** is replaced by atomic rename (a reader sees the old copy or the new, never a torn one), and **only when every finished directory has its marker**; otherwise the old one stays,
  the run says how many failed, and the exit is 1. Before the rename the copy's `attempts.run_dir` values get D prepended (and `meta` records `fetch_run_dir_prefix` and `fetch_source`): the directories sit at
  `D/<the recorded absolute path>` and the pipeline reads the recorded path, so **`--campaign-root D` is all `cut` and `analyse` need** (`run` too), with no pull step and no ssh. Do not move D afterwards.
- Stdout on success: one line of counts (`runs`, `finished_dirs`, `pulled`, `skipped`, `store_bytes`, `seconds`, `dest`). The first fetch into a new D pulls every finished directory (the store lands only
  when all are in); later ones pull what finished since. Put ssh connection reuse in `--ssh` (`-o ControlMaster=auto -o ControlPath=... -o ControlPersist=60`) to save the per-directory connection setup.

## B's extra dispatchers: several stores, one snapshot (`snapshot/bmerge.py`, `snapshot/bindex.py`)

Some seed-1 runs are made by extra dispatchers on other providers, each with its own store, run-directory mirror, root and space. The space has site-g's name and other file ids,
so each provider has its own full layout index. Science's rulings (#34): B's run keys equal main's; a run both reach is decided by the FIRST STARTED attempt, and the duplicates are counted.
The seam is the store: the frozen `run_pipeline` writes every output once, over one merged store; nothing it writes is merged or rewritten. New code is in `snapshot/` only (`tools/` and `pcache.py` are in
the pipeline cache's key: touching either invalidates every cached entry).

    # 0. once per provider: its index = the source index with the provider's own ids.json (read-only REST: one lookup and listings; the token is read from a file, never printed)
    python -m snapshot.bindex --src-index-root <main's index root> --out-index-root <new root> --provider-host <H> --space-name <S> --token-file <F>
    #    <new root>/layout/{index.npz, ids.json, digest.json}; Production for it needs --data-dir <main's s1z> (its s1z is not under the new root)
    #    refuses ids that differ in path set from the source's, or equal the source's (the provider resolved to site-g), and an output that fails fullindex.load_full_index
    # 1. each store is a `snapshot.fetch` mirror (own --dest, so own fetch_run_dir_prefix). Fill each provider's cache on its own store with its own index:
    python -m snapshot.pcache fill --campaign-root <B mirror> --cache <B cache> --index-root <B index root> --data-dir <s1z> ...
    # 2. the merge: main + B stores -> one campaign root (counts on stdout; providers.json and merge.json beside the store)
    python -m snapshot.bmerge stores --main-root <main mirror> --b b1=<B1 mirror> --b b2=<B2 mirror> --out <M>
    # 3. config: {"merge_root": "<M>", "providers": {"site-g": {"cache": ...}, "b1": {"cache": ..., "index_root": ..., "data_dir": ...}}}
    #    every provider but main MUST name its own index_root and data_dir (refused otherwise, and refused if it is main's index): a missing one would label its runs with main's file ids.
    #    the store carries who owns each run (meta bmerge_providers, through the cut); providers.json must agree with it, or the assemble is refused
    # 4. the snapshot, unchanged except two flags: --campaign-root is <M>, and --providers <config> replaces --pipeline-cache (the two are exclusive)
    python -m snapshot run --campaign-root <M> --providers <config> --t ... --cap-s ... --out ...        # (or `cut`, then `analyse`)

- **Who wins:** per run key the earliest started attempt (`state != 'unstarted'`), compared as UTC; ties go to main, then B in argument order. A store that never started a run does not contend; if none did, the earliest deferral, else main's row.
  The winner's run row and all its attempts go in; the loser's are dropped, so the infra account holds one store's attempts per run. `merge.json` counts duplicates, winners, ties, the losers' attempts and usage,
  the duplicates whose loser finished while the winner did not (`loser_done_winner_not_done`: first started wins whatever came of it), and those `Store.counted_starts()` (a deferral is a start) would have decided the other way.
- **Refused, nothing written:** a B run key main lacks, or one whose seq/block/instance/option/layout/model/seed/exclude flag differs; two attempts naming one run directory; with the prefix check (the CLI's default): a store with no
  `fetch_run_dir_prefix`, two stores with the same one, a run directory outside its store's prefix. The sources are copied (`cut.copy_store`), never opened in place.
- **Labelling:** per provider that won a finished run, the cut reduced to its runs goes through the unmodified `pcache.assemble` with that provider's `Production` and cache (main's cache keys are unchanged), the per-run results are kept as they
  leave the pool, and the frozen `run_pipeline` is replayed over the whole merged cut with them. A run no pass returned, or two did, is an error. A provider's own planned-miss limit applies. `OUT/work/merge/` holds `providers.json` (run key -> provider; main = site-g) and
  `assemble.json` (per-provider hits and misses); `SNAPSHOT.json` has `merge` (counts only). Join `providers.json` to `run_labels.jsonl` by `store_run_key`. Sealed like the rest of `OUT`.

## What comes out, and what to keep out of GitHub, comments and lane reports

- stdout is one line of whole-cut counts (`runs_in_cut`, `done`, `unfinished`, `exhausted`, `no_outcome_as_exhausted`, `pipeline_failed`) and a manifest hash. Only that line may be quoted.
- `OUT/tables/` (the contrasts and every table), `OUT/pipeline/` (labels, per-option counts), `OUT/.captured/` (what the libraries printed, with per-option
  counts, and `error.txt`), `OUT/work/cut/` (the store copy) and `SNAPSHOT.json` are sealed: do not paste, quote, commit or push any of them, or any run key,
  option count or contrast figure derived from them. `OUT` is mode 700, but any session of this user can read it; keeping it sealed is an instruction.
- Nothing else is written outside OUT (the guard refuses it; `.pyc`, temp and cache directories are pointed into `OUT/.tmp`).

## Which layout a run read, the bypass count, and the own-layout and within-environment tables: `snapshot.layoutread` and `snapshot.layoutown` (#34)

A run reads one layout (the directory its layout is stored in) and may read the sibling directory. The frozen detector maps a read against the run's own manifest only, so a sibling read
is an unmapped line there. These two modules run after the snapshot, read a sealed directory's frozen inputs and write only `<seal>/layout/`; nothing in `icsa/` or in the pinned H3 measure changes.
`snapshot_tool_sha256` in a later `SNAPSHOT.json` changes with the new files (recorded, not refused).

    python -m snapshot.layoutread read <seal>      # layout/layout_read.csv and layout/bypass.csv (+ counts_by_reason.json, bypass_summary.json, layout_read.meta.json)
    python -m snapshot.layoutread h3   <seal>      # layout/h3-own/: the pinned measure, unchanged, on platform rows in which sibling-reading runs are not_observed:layout_read_*
    python -m snapshot.layoutread own  <seal>      # layout/own-only/, env-vm/, env-hpc/ (each the frozen analysis on a subset of UNITS), environments/beside/, own-only/beside/
    snapshot/layout-stage.sh <t> <seal>            # the three as one timed stage of the interim driver (substages in layout/stages.jsonl)

- `layout_read` (own | other | both | none | empty) is defined the same for every option (science's ruling): the gate's content bytes for T, T-unpaginated and D, and for ALL options the run's own
  audit lines mapped against both layouts' manifests (an `open_file*` or `remote_read`; the lines carry no bytes). Union of the sources; any byte or line counts, no threshold (`bytes_own`,
  `bytes_other` are in the file). **M's oneclient performance-log bytes are beside it**: `bytes_own_perf`, `bytes_other_perf`, `perf_layout_read`, and `layout_read_with_perf` (the union with them).
- A run with no source that stands has an EMPTY `layout_read` and its `reason` (no_log, log_lost, audit_not_observed:<reason>, audit_changed_since_seal, unmapped, ...): never guessed, never `none`.
  `other_seen=1` marks an empty run whose partial evidence already shows a sibling read.
- **Bypass count** (`bypass.csv`; sealed, reported, never a filter): for each REST run (T, T-unpaginated, D), the files the provider's audit lines show the slot user opening or reading that the gate
  log never served (a gate request of any method or status counts as served). Compared only when both logs stand; `status` says why not. The terminal shows only `it_happened=yes|no`.
- **M stalls** (`m_stalls.csv`, M runs only): `max_read_gap_s` (the longest gap between two read events: the oneclient perf log, else the audit lines; `max_read_gap_source` says which) and `hung_task_lines`
  (the host kernel's `blocked for more than` lines in the run's lease window, from the copy the driver freezes into `frozen/kernel-hung/<provider>__<host>.log`; an empty log is 0, a missing one is unknown).
  `stall_evidence` tells, for a gap of 5 minutes or more, whether a read call was open 5 minutes at the FUSE level or the host logged a hung task (a stall) or neither (thinking, computing, or a hang the logs do not
  carry). The terminal shows totals only: M runs, with a gap of 5 minutes or more, with a hung-task line, how many of each are unknown, and the long gaps with / without stall evidence.
- **Backend shares** (`backend_shares.csv`): per option x model across the cut, the runs by the backend that served the model (site-a, site-ba, site-b, anthropic: the winning attempt's `backend` and `slot`;
  site-ba = the slots in `frozen/site-ba-slots.txt`, default gemma-107) and by the environment the dispatcher ran in (vm, hpc), with each one's share of the cell. The terminal shows only `backend_shares_rows=N`.
- **Evidence cache** (`snapshot/layoutcache.py`, optional): `read --cache DIR` finds a run's evidence (what its gate log, perf log and audit lines show, not a row) in DIR and reads only the runs it has not
  seen; `python -m snapshot.layoutcache fill --merged-root <seal>/M --cache DIR --audit-root ... --jobs N` fills DIR from a merged store outside any snapshot, so an interim reads almost nothing. An entry is
  used only when everything its evidence depends on is what it was (the code that reads the sources, the manifests, the provider's id table, the sources' size and mtime, the audit record and the exclusion
  windows of the run's slot); the environment, the kernel journals, the backend and the slot are made at read time and never cached. DIR is mode 700 and sealed.
- **H2's bytes** (science, #34 12:27Z): `bytes_between_sites` is not measured on HPC (empty, never 0). `bytes-measured/` re-runs the frozen analysis on the units whose compared options (T, D, M) were all measured,
  with `beside/h2_bytes.csv` (the bytes rows of h4_directions, primary vs these units) and `layout/bytes_units.json` (how many units qualify; the terminal shows one total, `bytes_units_qualifying=N`).
  `gate_bytes.csv` keeps the gate's `bytes_to_sandbox` per run for T, T-unpaginated and D on both environments, and `bytes_relation.csv` relates it to the bytes between the sites on the VM runs where both
  exist; the two counts are separate columns and never mixed.
- **Units** are instance x layout x model. `own-only` drops a unit, for levels and contrasts alike, when any of its runs (T-unpaginated included) read the sibling; units with no evidence stay and are
  counted; `units_by_model.csv` per variant has the counts per model. `env-vm` / `env-hpc` keep only the units whose runs ALL ran in one environment (the owner provider: a `site-a` line of the provider
  table, or an `icsa-site-a*` name, is HPC; the rest is the run VMs); `layout/environment_units.json` says how many units qualify. The H3 reading stays per run.
- stdout is totals only; every output stays in the sealed directory.

## The coder replay: a numeric check on the coders (`snapshot.coderreplay`, #34; science 5 Nov 11:09Z)

For every packet of set R or C whose two coders both answered, with `both_agree_exactly` and a saved mask: the coders' extent (required minus the (day, sea-cell) pairs their extraction leaves out,
rebuilt from the answer and checked against `compare.py`'s `missing_extent_sha256`) is turned into a reference by the FROZEN `scoring.reference.counterfactual`; the full reference is the frozen `full`
detection and must equal the frozen truth. `f1_full` and `f1_extent` are the cell-day F1 (`scoring.masks.cell_day_f1`, sea cells) of the run's mask against each. No reader, no LLM. If the coders' extraction is right,
a run labelled omitting matches its own extent better than the full one, and a complete run matches the full one; other errors of the agent stay visible as `f1_extent` below 1.

    snapshot/coder-replay-stage.sh [start|collect|both] <t> <seal>     # after the unseal sub-stage; writes <seal>/coder_replay/{coder_replay.csv,meta.json,work/} (mode 700)
    python -m snapshot.coderreplay plan|compute|collect|pack ...        # the pieces (see the module docstring)
    python -m snapshot.coderreplay_remote setup|run|status ...          # the site-a holder jobs (REPLAY_JOBS), their /tmp and a 700 directory on scratch

- `start` plans on this host and runs the detection on the holder jobs IN THE BACKGROUND, inside `REPLAY_BUDGET_S` (default 900 s); `collect` waits for it up to the deadline and writes the table. Both is the default.
- The cache `REPLAY_CACHE` (default `/mnt/volume2/icsa-2027/snap-coder-replay-cache`, 700) holds DETECTIONS by (code+data, instance, extent digest), not F1 values, and each extent's summary: a later interim computes only the extents it has not seen
  and does not read the answers of runs it has already planned. A result from other code, for another digest or with a bad checksum is never served.
- **The registered discrepancies on the coders' extent** (science, #34 12:19Z): `cf_computation_f1` (the run's events against the reference's on the coders' extent) and `cf_omission_f1` (that reference's events against
  the full one's), with the registered `events.match_events` definitions, empty with a note when the reference has no event; `f1_extent_vs_full` (the same two references, cell-day); `coders_coverage_baseline/target`
  (1 - missing / required, what `coverage.py` hands the analysis); and, for the runs the INSTRUMENT labelled complete or omitting, `instrument_coverage_*` and `instrument_cf_*` as the pipeline scored them. **Why the pipeline's
  `cf_computation_f1` is null and `cf_omission_f1` ~0 on resolved runs:** the scorer builds the counterfactual on A_lo, a lower bound for a run the instrument left `unknown`, so it has no event; the coders' inspection replaces
  only the coverage (`apply_inspection_coverage`). Fixture: `tests/snapshot/test_coderreplay_discrepancy.py`.
- **`coder_causes.csv`** (`snapshot/codercauses.py`): one row per run the coders resolved to omitting (route inspection), `cause` = the frozen rule coder (`icsa.causes.rules.code_run`) on evidence with the coders' exact extent as
  `analysed` and read/listing not observed, `cause_window_rule` (a whole-day window shortfall of one part counted as wrong_subset), `cause_detail` (the window's shape: whole years / `one_edge_day_per_year:lead|trail` / edge days / cells),
  or `why_not_coded`. Cannot be coded without the read extent or the listing: truncated_listing, skipped_or_partial_read, read_not_used, wrong_subset_region.
- **The second-coder sheet** (`python -m snapshot.codersheet <seal> --answers-root .. --out ..`, run once on a finished seal): the repository's own 20% sample stratified by option x layout x code, code hidden, opaque shuffled ids,
  `key.csv` kept back, transcript and code copied under `files/<id>/`; beside the pipeline's `out/pipeline/second_coder`.
- **Where it runs:** interims on the four holder jobs (`REPLAY_JOBS`), the fixed snapshot (`SNAPSHOT.json` final=true) on one node (`REPLAY_FINAL_JOBS`, job job_1), nice, at most 16 processes and no more than the cores free at the time.
  The stage reads `REPLAY_TREE` and `REPLAY_PY`, not the driver's `TREE`/`PY`.
- One row per R/C packet: `replayed`, `f1_full`, `f1_extent` (empty with a note when the reference has no active unit), the missing baseline/target days (counts and date ranges), missing cell-days by part,
  cells missing every day, and `why_not_replayed` per run: not_in_population, no_run_dir, not_coded, coders_pending, coder_no_valid_answer, extraction_not_exact, extractions_differ, answer_unreadable,
  answer_changed_since_decision, extent_rebuild_mismatch, no_run_record, mask_missing, mask_invalid, truth_mismatch, compute_failed:<code>, compute_unavailable (no node answered), time_box.
- It never fails or holds up the primary. Exit codes: 0 clean; 8 no coding decisions in the seal; 9 a step failed (plan, collect); **10 degraded**: the table exists but some runs that could be replayed were not (site-a
  unreachable: `compute_unavailable`; the budget: `time_box`; a failed job: `compute_failed:<code>`; `truth_mismatch`). The one line to log is `coder-replay result: rows=.. replayed=.. not_replayed=.. degraded=.. ...`.
  Budgets: `REPLAY_PLAN_BUDGET_S` (900) for the plan, `REPLAY_BUDGET_S` (900) from the end of the plan to the end of collect; the site-a side is killed by process group at the deadline.
  The table's first line is `# snapshot final=<true|false|unknown> t=<t>` (read with `skiprows=1`). stdout is totals and seconds only; the table and the cache are sealed.
