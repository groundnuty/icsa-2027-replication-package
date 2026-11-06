# Instrument validation (#9): the matrix at 4bc98fd FAILED its gate; a record, not evidence

**This run does not satisfy pilot criterion 2.** It is kept as the record of the failure and its cause. The
evidence for criterion 2 is the rerun on the fixed head, in its own folder.

**Result:** 238 of 274 cells pass every check and 36 fail, all 36 from one defect in the matrix's cached layout
index. The instrument code that runs in the sandbox is not implicated.

## The run

    python -m icsa.instruments.validate --work <dir> --jobs 3 --resume --commit 4bc98fd

Three processes on 1 and 2 Nov 2026, on the host's data volume, from `git archive 4bc98fd` snapshots:

| process | from | to | how it ended |
|---|---|---|---|
| 1 | about 21:08Z | 21:24:54Z | SIGTERM (`logs/run-4bc98fd-2026-11-01T2124Z-sigterm.log`) |
| 2 | 22:09:21Z | about 23:48Z | the host froze; its log was empty |
| 3 | 00:49:42Z | 00:53:44Z | finished (`logs/run-resume-2026-11-02.log`) |

Process 3 ran from a snapshot rebuilt after the reboot wiped the first one, on the same Python and `uv.lock`. Its
code stamp, `45b3d3d8…`, equals the stamp on all 245 saved rows, so `--resume` reused them, and it ran the other 29
cells. A resume reuses a cell only if its `row.json` has that stamp and a label, `row.json` is written only after a
labelled finish, and `run_case` deletes a cell's directory before running it, so a cell cut off by the freeze was
redone, not counted. Group RSS peaked at 747 MiB in the 30 s samples (`logs/memory-watch-2026-11-02.log`).

**The merged head:** `icsa/instruments/confirm.py` is the only file under `icsa/instruments` that differs between
4bc98fd and f7cac04 (#92), and the matrix's code stamp computed on f7cac04's tree is the same `45b3d3d8…`.

## What failed

`validate.main` returns 1 for this summary (the unknown share and `source_variants_disagree`, among its gates).
The exit code itself was not captured, since the launcher did not record it.

Every cell of these two groups comes out `unknown`, reason `unidentified_source`:

- `source_memory` and `source_memory_skip` in all 5 options and both layouts: 20 cells;
- `masked_*` under T in both layouts, which decode with `netCDF4.Dataset(memory=...)`: 16 cells.

These 36 cells account for the whole of:

- the core unknown share of 13.6% (36 of 264), over the 10% gate;
- `loaded_not_exact` and `read_not_exact`, 36 each;
- `complete_not_called_complete`, 18 (the complete half of them);
- `source_variants_disagree`, all 20 groups.

The other 10 unknowns are `stress_print`, unknown by design and outside the core.

**What passed, on all 274 unless stated:** no cell errored. No omitting run was called complete. Analysed extents are
exact on every resolved run. Every upper bound is sound. Every read was observed, and `read_beyond` is exact.
`listing_ok` holds everywhere, and no field the rule requires is `None`. `listing_disagrees` fires on exactly the
three S1 `listing_subprocess` cells (T, T-unpaginated, D), as the scenario is written. `decoded_not_delivered` is
empty. There are no tracer internal errors and no bypass-scan hits on the scripted code. `delivered_not_decoded`,
descriptive, is on 15 cells.

**Scope:** `gates` is `local-sim`; `real_confirmation.runs` is 0. This is the local half of criterion 2 only.

## The cause

`LayoutIndex.save` wrote the layouts but not `shas`, the content hashes that name an in-memory source, and `load`
returned an index without them. `validate.make_data` reuses its cached index when the data digest matches. So:

- process 1 built the index at 21:08:00Z and held the hashes in memory, but finished only 9 cells, none of them
  in-memory, before its SIGTERM;
- processes 2 and 3 reloaded the cache with 0 hashes, and every in-memory cell ran in them, from 22:16Z on.

`--resume` is what exposed the defect: an uninterrupted first run would not have hit it.

**Diagnostic, not evidence** (`diagnostic/relabel_probe.py`, with `relabel_probe_36.jsonl` and
`relabel_probe_all.jsonl`): all 274 cells relabelled offline from their kept traces, with the cached index as loaded
and then with the hashes added. As loaded, all 274 reproduce their committed rows. With the hashes, all 274 pass every
check: the right label (`stress_print` stays `unknown`), and exact analysed, loaded, read and read-beyond extents. The
hashes change exactly the 36 in-memory cells and no other. These are relabels of old traces, so the rerun, not this,
decides the result.

## Which runs could see a hashless index

From `git grep` on main at 0200828 (2 Nov), and `load` on the real file:

| caller | path |
|---|---|
| `validate.make_data` | the defect above: matrix cells in a process that reloaded the cache |
| `fullindex.load_full_index` | sets `shas` from #3's manifests right after the load: 15341 hashes on 15341 layouts |
| `confirm.py:127` | through `load_full_index` |

`label_run` is called on main only by `validate.py` and `confirm.py`, so on main no agent run and no confirmation run
could see one.

**The unmerged pipeline would have:** `Production.index` in `icsa/pipeline/resources.py` on `feat/2-run-pipeline` does
a bare `LayoutIndex.load` of its `--index` paths. On the campaign's own index file that gives 0 hashes and 0 ids.
No pipeline output exists yet, so no real run was labelled that way. The fix makes such a load refuse.
