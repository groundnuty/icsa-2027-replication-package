# Live check of the platform records, 1 Nov 2026 21:20:29–21:22:31Z (#11 part 2; science on #2, item 3)

**What ran.** `python -m icsa.faults.live_check --only T,D,M` at code e94adf7. Each option ran in its own real sandbox: image `icsa-sandbox:11live-58e5332`, built from main 58e5332; `real_sandbox.sandbox_config` with the `config/harness.toml` limits; untraced. Each held a lease on a slot user of its own option:

| run key | slot | user id | lease (UTC) |
|---|---|---|---|
| `s11live-212027-T` | T-1 | `3621f404…589b` | 21:20:29.253–21:20:49.759 |
| `s11live-212027-D` | D-1 | `38eadd49…9ce6` | 21:20:50.441–21:21:06.372 |
| `s11live-212027-M` | M-1 | `8f3e857b…8ddc` | 21:21:06.972–21:22:30.640 |

**What each option read.** The plan is in the driver, and the stamps are in `<opt>/live.json`. Reads went through `insandbox.Paths`, the campaign's mechanism.
- **T:** `sst_19820105.nc` through xarray over the fsspec onedata file; 3 s later, bytes [0, 15241) of `sst_19820106.nc`. That's the header only; every S1 file's data starts at 15241.
- **D:** `fs.get` of `sst_19820105.nc`.
- **M** (proxy I/O, perf log on):
  - exec 0: 0105 through xarray, the 0106 header, then 0107 through xarray;
  - after a 10 s pause, exec 1 in a new process: 0107 again, then 0105 again;
  - exec 2: 0108 read twice in one process, 3 s apart, as raw bytes.

**What is here.** Only our own lines, filtered at the source:
- `audit.log`: 411 lines, the three users above, 21:19–21:23Z;
- `traefik.jsonl`: 18 lines carrying our run keys;
- `M/read_write_perf-*.csv`: the M sidecar's perf log;
- `T/`, `D/`: the gate logs;
- `driver.log`.

The oneclient INFO log is not kept. None of the lines holds a token: Traefik logs no auth header.

## Findings

**Time zone.** The audit log is UTC, with milliseconds. T's content GET has Traefik `StartUTC` 21:20:42.786Z. The audit lines for the same read are `open_file_with_extended_info` at 42.790, `remote_read` at 42.800 and `release` at 42.806. All of them fall inside the host's stamps of that read, 40.397–42.977Z. The perf CSV's time of day is UTC too: its first `FsLogic,read` is 21:21:28.1165, and the audit's first M `remote_read` is 21:21:28.108.

**Request types per option.** Each option is calibrated against its own lines.
- **T and D, per REST GET:**
  - `fuse_request::resolve_guid_by_relative_path` (its path is the space id)
  - `fuse_request::file_request::get_file_attr`
  - `…::open_file_with_extended_info`
  - `…::synchronize_block`
  - exactly one `proxyio_request::remote_read`
  - `…::release`
- **M, per open, through oneclient in proxy I/O:**
  - `…::get_child_attr`, `…::get_file_location`, `…::open_file`
  - on the first open only: `fuse_request::get_helper_params` and `create_storage_test_file`
  - N × `proxyio_request::remote_read`: N = 30 for an xarray read, 2 for a raw 212 KB read, 3 for the 15 KB header
  - `…::fsync`, `…::release`
  - a listing is `…::get_file_children_attrs`
- The sandbox's own I/O-mode probe adds 207 `get_file_location` lines on files that were never read (sst_2023…). They are neither an open nor a read.

**header_only, S1.**
- **T, Traefik.** The 15,241-byte read went out as `Range: bytes=0-173179`, the whole 173,180-byte file. fsspec reads in 5 MiB blocks, and every S1 file is smaller than that. The detector credits the day, so a header read looks like a full read.
- **M, perf.** The same read reached oneclient as FUSE page reads, `FsLogic,read` [0,12288) and [12288,16384). That is 1,143 bytes past the first data byte, and v1's `min_overlap_bytes = 1` credits the day.
- **The audit log** credits it in every option, as registered (unobservable by design).

Both Traefik and perf were registered as **observable**. Under detector v1 these are class changes, reported before anything was written. Science's amendment 12 (#11, 21:37Z) brings detector v2: on byte records, a day is read only when the served bytes cover its whole chunk. Under v2 the M perf cell stays observable, because pages [0,16384) do not cover the chunk, while the T Traefik cell stays unobservable, because the whole file is served.

**warm_buffer (M).** A re-read was never served from a cache. oneclient fetches the data again on every open:
- **In a new process after 10 s** (exec 1, 0107 + 0105 = 367,625 B): the sidecar's bridge rx was 404,134 B.
- **In one process, 3 s apart** (exec 2, 2 × 212,147 B): it was 434,781 B.
- **In the perf CSV,** every re-read has its own `ReadCache,prefetch` rows.
- **In the audit log,** every re-read logs `open_file`, the same `remote_read` count as the cold read, and `release`.

So the scripted warm_buffer condition leaves the same audit lines as cold. A read served from a warm client buffer could not be produced by re-opening.

**M and Traefik.** M does not pass the gate. In M's window, Traefik shows only `GET /clproto` websocket upgrades, with no run key, no User-Agent and no file. Traefik is not a record for M.

**Traefik v3.5.3 fields.**
- `StartUTC` is RFC 3339 with nanoseconds.
- `Duration` and `OriginDuration` are integers in nanoseconds.
- `request_Range`, `request_X-Icsa-Run` and `request_User-Agent` are present.
- `RequestPath` carries no query string.
- `ClientHost` is 198.51.100.185 on every line.
