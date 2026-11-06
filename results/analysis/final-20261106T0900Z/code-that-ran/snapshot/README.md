# Interim snapshots (#34)

A snapshot at time `t` covers the runs first started by `t - cap` (counted start: the first started attempt or the deferral; a retry never moves it).
Each is done as of `t`, exhausted as of `t`, or unfinished (not waited for; see below for how the analysis counts it). Runs that started later are out, finished or not.
**The paper's analysis (amendment 29(c)) is one fixed snapshot: `--t 2026-11-06T00:00:00Z`, `--cap-s` = the final time cap, `--no-outcome as-exhausted`, `--final true`**, with
coding of those runs stopped at 06:00Z (a label not coded by then stays `unknown`). `--no-outcome` is required, no default. `as-exhausted` turns every in-cut run
with no outcome at `t` into an exhausted run in the store copy, before the unchanged pipeline and analysis run, so it leaves the primary denominators, is reported
per cell and counts as time-capped and a failure in the sensitivity row. The converted run keys are written to the copy's meta `snapshot_no_outcome_runs`, so
`exhausted_per_cell` splits `n_infrastructure` from `n_no_outcome_at_snapshot`. `report` (earlier, descriptive parts) leaves them `unfinished`, in the cohort (the cut stamps
`cohort_cut_utc` at `t - cap` plus a second), and "never imputed" holds for that case and for the primary analysis in both. Earlier parts carry no claims: Holm decisions
and smallest-effect verdicts are read only from the fixed snapshot.
`--final {true,false}` is required, no default. **`--final true` is accepted only on the fixed cut** (the instant 2026-11-06T00:00:00Z, however spelled, with
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
