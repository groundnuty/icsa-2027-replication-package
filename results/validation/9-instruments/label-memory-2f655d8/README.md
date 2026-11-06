# Label memory: the to_units fix and its identity evidence (#9, 2 Nov)

One real T label on S1 went over a 60 GiB cap and froze the old host. This directory holds the measurements before and after the fix on
`fix/9-label-memory` (`969f9fa`, tests up to `2f655d8`, on top of `fix/9-index-shas` `40ca8f2`) and the evidence that the fix changes no answer. All of it ran on the VM `.23` under `memcap`; nothing touched site-g.

## Why it took that much memory, and the fix
`readext.to_units` held every unit a byte log covered as three int64 arrays. A real file's chunk is a whole day's grid, 657,926 units, and what a log covers does not depend on the instance's box: about 1e9 units for T on S1, 1e10 for a whole S2 file. `covered_pieces` now yields a wholly covered chunk as a block, never expanded, and `UnitTally` keeps one packed grid bitmap per day. M's campaign log does not reach `to_units`, so M was never affected.

The instruments hash stays `d7ca5cfbe936401c86b58d7affca42a7e0f4cb2a7f185973b64555b7640e9c67`, computed at `40ca8f2` and `969f9fa` (`logs/identity.log`); nothing under `icsa/` changes after `969f9fa`.

## What the runs are
- **oracle:** real gate logs from site-g (`oracle-results/20261101T132535Z`), with empty trace directories. They show the byte-log path only.
- **traced:** validate's scripted agent under the real tracer on real I01 files through the local server (`scripts/gen_traced.py`).
- **K local sim:** the oracle's own I01 code replayed in the real `Sandbox` with the real gate, the image's real platform client and a mock with site-g's real file ids (`scripts/k_sim.py`). No network, provider or federation behaviour.
- **K-run-1, K-run-2:** two runs of a blind test set, real sandbox and tracer, M only, a plain directory in place of oneclient. Timing and memory are in `logs/results.log`. Their outputs are not here, and M's outside view on them (case A of `scripts/m_outside.py`, 7 of the 19 checks, all passing) is reported by its checks only: the set's cases and verdicts stay out of the repository.
- **Calibration perf logs:** real oneclient logs from site-g, whose runs really skipped files or chunks; no trace.

**No real M run has both a tracer and its own perf log,** and no T or D run on S1 from site-g has a trace. The M and T/D results here are the closest available.

## Identity
| Comparison | Result | Where |
|---|---|---|
| Random layouts, old body against new, with chunk edges | 300 + 100 cases pass; 14 of 14 deliberate breaks caught | `tests/instruments/test_units_tally.py`, `scripts/mutate.py` |
| All 274 cells of the failed matrix relabelled at both heads, whole output | byte-identical, sha256 `b1db7735…`, 0 errors | `outputs/relabel-9p-mem.jsonl`, `logs/identity.log` |
| Old code a piece at a time on real byte logs: T S1, D S1, T S1 traced (all 1,544 files), T S2 (1,655 of 1,987 chunks), D S2 (1,888 of 15,340) | 0 differences; new pieces add up to the new whole | `logs/identity.log` |
| Cause inputs through `label_run` on 9 cases, whole logs, `to_units` stubbed at both heads, against the fixed code | identical; 23 of 23 hand-worked checks | `outputs/cause-*-{stub,real}.json`, `logs/cause_runs.log` |
| Old against new on short real slices (30 content lines per S1 log, 6 per T S2 log), every field | identical on all 8 cases | `outputs/cause-*-slice.json`, `logs/cause_slices.log` |
| Cause-input comparison broken on purpose | 8 of 8 caught | `scripts/mutate_cause.py` |
| M's outside view, planted reads and real perf logs | 19 of 19 hand-worked checks, identical at both heads | `outputs/m-outside-*.json`, `scripts/m_outside.py` |
| The oracle's own I01 code on K local sim, T, D and M: label and reasons | `unknown`, `unmodelled_op` and `escape`, in all three | `outputs/new-ksim-{T,D,M}.json` |

`read_beyond_days`, `delivered_not_decoded` and `decoded_not_delivered` do not pass through `to_units`, so label and cause-input equality alone cannot test this fix: `fetched` and `delivered` do, and the piecewise and slice comparisons are what cover them. In the 274 cells `decoded_not_delivered` is never non-empty; its non-empty cases are the planted ones.

## Files
`outputs/old-*`, `old8-*`: results before the fix, under 60 and 8 GiB caps. `outputs/new-*`: after it, under 4 GiB. `logs/results.log`: exit code, wall time and peak of each capped run. `logs/t1-orig.rss`, `t1-orig.err`: the unfixed T S1 run's memory over time and stack, killed at the 60 GiB cap at 275 s. `logs/suite-*.log`: the two suites.
