# The instrument validation matrix at 2f655d8 (#9, criterion 2, 2 Nov)

The matrix on the code that will label the campaign: `fix/9-label-memory` at `2f655d8` (the index with its hashes, `40ca8f2`; `to_units` per day, `969f9fa`). A fresh work dir on the VM `.23`, no resume, `--jobs 3`, under a 16 GiB cap, 03:05Z to 04:36Z on 2 Nov, 91 min. Local path (`gates: local-sim`), as the matrix always is; the real-path confirmation set is the other half of criterion 2.

**It passes its gate.** 274 of 274 cells: no omitting run called complete, no failure, no cell resumed, `unknown_share_core` 0.0, and every other gate list empty (`summary.json`).

| True label | Labelled |
|---|---|
| complete (122) | 122 complete |
| omitting (152) | 142 omitting, 10 unknown |

**Against the failed run at `4bc98fd`:** exactly 36 cells change, all from `unknown` to their true label, 18 complete and 18 omitting: 20 in-memory source cells, 16 masked. They are the cells the hashless cached index broke, as the failed run's relabel predicted (`../4bc98fd-failed/README.md`).

**What this does not say (science agent, #9).**
- `unknown_share_core` 0.0 is not a forecast. The matrix cells are mostly vectorised analyses of known shape, the literal oracle itself comes out `unknown`, and real agent code will sit higher. Inspection under amendment 11 is there for that.
- `gates: local-sim` is the local half of criterion 2, which stays MISSING until the real-path confirmation set passes on this head.

`instruments_sha256` in `summary.json` (`a15303bb…`) is the hash of every code file a matrix cell runs. It is not the campaign's pin, `d7ca5cfb…`, which hashes the in-sandbox set only; that one was computed separately at this code (`../label-memory-2f655d8/logs/identity.log`).
