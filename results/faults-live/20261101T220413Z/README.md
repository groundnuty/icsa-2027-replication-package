# Live check, part 3: prefetch_on with the frozen flags, and S2 with the middle chunk skipped (1 Nov 2026, 22:04:43–22:06:55Z)

**What ran.** `python -m icsa.faults.live_check --only Mpre,T2skip,M2skip,M2skippre` at ebc324a, on the same image and config as `../20261101T212027Z`. Slot leases: T-1 for T2skip, M-1 for the others. Only our own lines are kept: 323 audit lines and 6 Traefik lines.

**prefetch_on, as science froze it (#11, 21:40Z; amendment 12).**
- **Flags:** `--read-buffer-prefetch-duration 30 --read-buffer-max-size 1073741824`. Both are recorded in `Mpre/live.json` and in the sidecar's `oneclient_args`. Calibration uses exactly these.
- **This run supersedes the 10 s run** in `../20261101T214104Z/Mpre`.
- **Full read of `sst_19820111.nc`** (xarray):
  - audit: `open_file`, 30 × `remote_read`, `release`;
  - perf: 37 `FsLogic,read` rows, the same as cold.
- **Header read of `sst_19820112.nc`** (15,241 B):
  - audit: `open_file`, 3 × `remote_read`;
  - perf: `FsLogic,read` [0,16384).

**S2: chunk 200 read, 201 skipped, 202 read, through one open file.** Day 200 is in 1982, never required. The chunks are:
- 200 = [38840395, 39096343)
- 201 = [39096343, 39345065)
- 202 = [39345065, 39576935)

**T** (`fs.open`, onedatarestfsspec with read-ahead):
- One GET, `Range: bytes=38840395-44339222`, 206, 5,498,828 B. That is chunk 200 plus exactly 5 MiB.
- Skipped chunk 201 is served whole.
- Chunk 202 came from the client's cache, with no second request.
- Audit: `open_file_with_extended_info`, 2 × `remote_read`, `release`.

**M, default and with the frozen prefetch_on flags (identical):**
- `FsLogic,read` covers [38840395, 39098443) and [39345065, 39578537). The application's offset is kept, and the size is rounded up to whole 4 KiB pages.
- The page rounding reaches 2,100 B into chunk 201 (a 4,096 B row at 39094347) and 1,602 B into chunk 203. So chunk 201 is partly covered by client reads but never read whole: the planned v2 (full chunk coverage, amendment 12) would count it as not read, while v1 credits it.
- `ReadCache,prefetch` reached 6,196 B into chunk 201. The detector ignores those rows.
- Audit: `open_file`, 6 × `remote_read`, `release`.
