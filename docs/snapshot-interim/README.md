# Interim snapshots, the full path (#34, lane-snap)

Science's request (#34, 4 Nov 18:49Z): interim snapshots, each the FULL path: fetch, merge, cut, assemble, H3 measure, analysis; outputs to science only, sealed, read by no one but the
pipeline; every stage timed; the first at 5 Nov 00:00Z (cut = t - 490 min = 15:50Z), then every 6 h (06:00Z, 12:00Z, 18:00Z, 6 Nov 00:00Z); the whole path under 1 h.
Nothing here changes `icsa/`, `tools/` or `snapshot/pcache.py`, so the pipeline cache's key is untouched (checked: tree hash and pcache.py equal to 09ecc2c0's).

## What runs where (all on the dev host `handle_8-dev-agents`, every job under `memcap` and nice)

| piece | script (installed under `/mnt/volume2/icsa-2027/launch/`) | what it keeps |
|---|---|---|
| B mirrors | `b-mirrors.sh start\|stop\|status\|once\|merge` (loop every 15 min; after each pass it rewrites the coders' merged store `coding-merged/`) | one `snapshot.fetch` mirror per B host in `snap-b/<provider>` (read only on the B host; `VACUUM INTO` over a read-only connection into a temporary file outside the store) |
| B indexes | `b_index.py PROVIDER...` (once) | `snap-b-index/<provider>/layout/{index.npz,ids.json,digest.json,PROVENANCE.json}`: main's index with the provider's own ids (read-only REST, the provider's service user, token in memory) |
| B caches | `b-fill-loop.sh start\|stop\|status\|once` | `snap-b-cache/<provider>`: `snapshot.pcache fill` on that provider's mirror, index and cache, serial, jobs 6, memcap 4, nice 19; a guard stops a running fill's scope under 12 GiB MemAvailable |
| main's cache | the lead's `pcache-loop.sh` (unchanged) | `pilot-coding/private/pcache-09ecc2c0` (hits from the overlay tree: proved 262/262) |
| H3 extract | `h3-loop.sh start\|stop\|status\|once [name]` (loop every 30 min) | `snap-h3/<store>`: a consistent copy of each audit store (`h3_sync.py`, no lock on the pullers) with extract's own records; extract is incremental |
| the snapshot | `snapshot-interim.sh <t>` | `snapshots/interim-<t>/` (mode 700, sealed) |
| schedule | `snapshot-interim-sched.sh start\|stop\|status\|list` (NOT started) | `snapshots/sched/` |

The overlay tree `work/wt/snap-run` is 09ecc2c0 (the campaign head, the cache key's tree) plus main's `snapshot/` (bmerge, bindex, run). Its interpreter is the fill tree's `.venv` (Python 3.13.13, in the key).
Extract and the measure run from `work/wt/snap-interim` (main's `icsa/faults/mainaudit`; the pinned files are identical to fffb1983's, so the pin `ff35112e...` holds).

**Heavy jobs (the lead, 4 Nov 20:0xZ):** one extract at a time (`lane-snap4/extract.lock`, per store) and one B fill at a time (`lane-snap4/fill.lock`, per provider) may run BESIDE each other: memcap 12 + 4 = 16 GiB, with the fill stopped (its scope) whenever MemAvailable drops under 16 GiB and not started under 18. Each waits at most 2 min for its lock and otherwise skips that unit until its next round; a snapshot's H3 pass waits at most 10 min and otherwise lets the store's last completed pass stand (logged).
Extract skips an attempt whose perf CSV is over 1.1 GiB (`h3_extract.py`, counted in the loop log) rather than raise the 12 GiB cap.

## The driver, stage by stage (`snapshot-interim.sh <t>`)

1. `freeze_main` / `freeze_b` / `freeze_inputs`: waits for main's mirror loop (10 min) to make a store copy AFTER t (`fetched_utc - seconds`, since fetch.json is written after the rsyncs); `freeze_b`: an at-once fetch of every B store, same check.
   `state.sqlite` and `fetch.json` of each go to `frozen/<name>/`; `timings.json` notes how long after t each store was copied.
2. `merge`: `snapshot.bmerge stores` (first started attempt wins; duplicates counted) -> `M/`.
3. `cut`: `snapshot cut` at t - 29400 s, `--no-outcome as-exhausted --final false`, with `--campaign-tree` (the code check).
4. `analyse`: `snapshot analyse --providers bmerge.json`: each provider's runs from its own cache and index, the frozen `run_pipeline` replayed, then the analysis tables. `timings.json` splits the pipeline from the analysis by the snapshot's own log stamps.
5. `h3` (`snapshot-interim-h3.sh`): `extract_all` (one pass of the loop: fresh copy of each audit store, incremental extract), `join` (`h3_join.py`: each run's platform row from its owner's store), `measure` (pinned, `--scored` out/pipeline/scored_rows.jsonl).

Exit status: 0 clean; 6 a mirror was not fresh at t (a failed fetch writes `store_replaced=false` and leaves the old store, which counts as not fresh); 7 the H3 stage did not run clean or is not installed; other codes are the stage that failed (merge 4, cut 5, analyse's own). Every stage still runs after a 6 or 7, so the sealed outputs of the rest exist.

Terminal output is counts and seconds only (the `snapshot`/`bmerge` count lines, the join's account, stage timings). Nothing under `out/`, `h3/` or `frozen/` is read or printed.

## Choices to state to science

- `--no-outcome as-exhausted`, `--final false`, `--overhead/--fidelity-rows/--inspection-labels none` (override with `NO_OUTCOME`, `OVERHEAD`, `FIDELITY_ROWS`, `INSPECTION`).
- `MAX_MISSES` unset: pcache's own limit (max(20, 10 %) of a provider's runs) refuses a cold cache rather than spending hours; `MAX_MISSES=-1` lifts it.
- B's first run is 17:33Z on 4 Nov, so no B run is in the 00:00Z cut (15:50Z); B enters from the 06:00Z cut (21:50Z).

## Gaps (said, not papered over)

- Main's extract inputs are copied read-only at each freeze and each pass (`h3-loop.sh inputs`): `site-g_restart_log.jsonl` and `mirror/site-g-mon.jsonl` from .23, and `HOST=absent@<time>` for .23 and .8 (neither has a `quarantines.jsonl`). **`mirror/site-g-mon.jsonl` is a 2 MB tail** (8:41Z to now on 4 Nov), so a lease that ended before it begins cannot have its restart windows verified; only site-g's FULL `/data/icsa-mon/mon.jsonl` would cover main since 00:33Z. `snap-h3/inputs.env` overrides what the loop copies.
- The join across extract stores is new glue (`h3_join.py`); the measure takes one platform file.

## Added 5 Nov: more providers, the site-a replica, the HPC mirror

- **Providers** come from one table, `lane-snap4/providers.tsv` (`name ip [vm2|site-a]`); `add-provider.sh <name> <ip|-> [vm2|site-a]` adds one (index, first mirror fetch, loop restart). `vm2` hosts (site-t on .8) are reached only through `bin/vm2ssh`; `site-a` providers are pulled by `site-a_fetch.py` (a `snapshot.fetch`-shaped mirror from `state.sqlite.tar` and `runs/<name>.tar` on site-a scratch, with sidecar sha256) and indexed from a listing made on a node (`site-a_listing.py`, stdlib only, then `b_index.py --ids-dir`).
- **Extract**: main's lane plus two providers' lanes, each with its own lock and memory guard; the snapshot's H3 stage reads each store's last COMPLETED pass (its age against t is in the report) and fails only if one is older than 90 min. Shards of the switched-on phase: `h3-shards.sh` (written, started on the lead's word).
- **Mirror**: fetches in batches (the loop 4, the freeze 8), one ssh ControlMaster to the site-a login node.
- **Fills on the site-a node** (`site-a-fill-loop.sh`): the node (job job_1, 192 cores) holds a replica on tmpfs: the uv Python, the venv, a git clone at 09ecc2c0 with main's `snapshot/`, and the data at the SAME absolute paths (`tar --format=posix` keeps nanosecond mtimes); `sandbox.sif` is only the container whose binds put them there. A fill inside it gave entries byte-identical to this host's (3 runs, then all 34 of site-u: 150 s at 8 workers), so they are valid here. `replica_identity.py` prints the key's identity for comparison. Providers listed in `lane-snap4/fill-remote.txt` are skipped by the local lanes. The replica dies with the job: `site-a-fill-loop.sh stage` rebuilds it (about 3 min) plus the run dirs.
- **Scheduler** also runs the final (6 Nov 09:00Z, `FINAL=true`, `final-<t>`); `snapshot/cut.py` and `__main__.py` must be copied from the merged main (#166) into `work/wt/snap-run` first (hash checks verified in a scratch copy).
- **Unseal** (science, #34 22:55Z): every scheduled interim runs `snapshot-interim-unseal.sh` (population, report --unseal, labels, coverage, label filter) into its own sealed dir and analyses again with the labels (`out-coded/`); a direct run never unseals (`UNSEAL_ENABLED`).

## Added 5 Nov (later): recohort, the exclusion list, HPC audit, the pace line

- **`snapshot/recohort.py`** (in `snapshot/`, outside the walk; `--recohort true|false`, default true): a dispatcher stamps `out_of_cohort` against its LAUNCH's cohort cut (`scheduler.py:2193`), every started B store keeps 15:50Z, so a later cut (the final's 00:50Z) would drop B runs first started in between. After the pipeline and before each analysis every scored row's `out_of_cohort` is recomputed with the scheduler's rule against THIS cut's `cohort_cut_utc` (the counted first start, a retry never moves it). A no-op on every cut that does not pass the launch's cut (350 and 326 rows, 0 changes, on the two real earlier cuts). Totals in `work/recohort.json` and `SNAPSHOT.json`. 7 tests, 4 fail against a mutant that skips the recompute.
- **Exclusion list** `lane-snap4/h3-exclusions.tsv` (`provider, slot, from, to, reason`, UTC ISO): a lease of that slot overlapping a window gets `not_observed:foreign_lines` for its audit record (`snapshot/h3exclusions.py`, applied between the extract's records and its platform-rows summary through `h3_extract.py`); it is copied into every seal (`frozen/h3-exclusions.tsv`); lane-layout's bypass count reads it too.
- **HPC providers (`icsa-site-a-2..21`, third column `site-a`):** mirror = `site-a_fetch.py` (state tar + one tar per run on site-a scratch, through the login node, retried while the store lists a tar not yet exported); indexes from a listing made on a node (`listing_remote.py --via site-a`); fills on the site-a node with the others (`fill-remote.txt` = ALL); audit stores are lane-site-aaudit's (`provider-audit/icsa-site-a-N`), monitor file per `lane-snap4/site-a-mon-source` (`extract` = the derived first line approved by science, 5 Nov 03:01Z; each pass records the file used, the first real sample ts and the number of leases that rest on the derived line: `mon.used.json` -> `h3/mon_used.json`).
- **H3's measure** reads the scored rows WITH the coders' decisions (`scored_coded.py`, recohort applied) and, when the copy exists, the per-day truth of lane-h3b's relabel loop on .16 (`daytruth_pull.sh`); the label source and day-truth note go into `h3/measure/label_source.json` and `counts.json`.
- **Fault calibration:** `fidelity_score.sh make` scores a COPY of its finished root on .23 (never the live root: `score` writes into `--out` and `--partial` edits the ledger); the driver only `pull`s the latest into `frozen/fault/` (`FIDELITY_ROWS`, `H3_TABLE`).
- **Pace line:** `backlog.py` (not mirrored / not labelled / not coded with oldest ages, Sol against 95/99), one Markdown line, read-only.
- **Layout stage** (lane-layout, optional until installed, exit 9 on failure); its one loud word `BYPASS: it happened` is surfaced in the driver and the report.
- **Traps:** editing a script a loop or a long job is running (bash reads it incrementally): install by rename and restart between cycles; a cycle's `pgrep -f` pattern matches its own shell's command line.
