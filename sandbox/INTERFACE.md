# Interface specification (#7)

What the agent's code sees in each option, and which parts are the shipped Onedata client and which were
written for this study. Mechanism and tests: `README.md`.

## Shipped, unmodified
- `onedatarestfsspec` 25.0.0 + `onedatafilerestclient` 25.0.0 (25.2.0 behaves the same), used by T, T-unpaginated and D.
- `oneclient` 25.0 (FUSE) for M and M+.

## Written for this study
1. **T-unpaginated listing shim** (`icsa/sandbox/gate.py`, `_merged_listing`). It wraps only `GET /data/{id}/children`:
   the gate requests pages of `page_limit` (1000) and follows `nextPageToken` until `isLast=true`, then answers the
   client with one page holding all entries and `isLast: true`. Reads are identical to T. It sits in the gate, so
   `ls`, `find`, `glob`, `walk` and `du` all see the full listing. This is the **only** difference between T and T-unpaginated.
2. **D in-place-read guard** (`sandbox/hooks/icsa_option_shims.py`, D only). Any in-place remote read
   (`fs.open(...).read()`, `cat_file(start/end)`) raises at once, with no request and no hang:
   *"In this sandbox, files cannot be read remotely in place; download whole files with fs.get(remote_path, local_path) first."*
   `fs.get` streams the whole file with no Range header (into an existing directory it keeps the file name, as fsspec does).
   The enforcement is the gate, not the shim: any `content` request with `Range` in D gets HTTP 400 with the same message.
3. **D store-and-forward** (`gate.py`, `_store_and_forward`). For a range-less `content` GET under D the gate downloads the
   **entire** file from the provider to its own spool (disk, bounded by the file size) and releases the first byte to the
   sandbox only after the last one has arrived; the spool is deleted afterwards. So whatever the agent's code does (read
   1 KB and close, `iter_file_content`, raw `requests`), the transfer between the sites is the complete file, and no
   in-place remote read exists on the wire. The spool lives in the run's directory (`ICSA_DATA/sandboxes/<run>/gatelog/spool`, on /mnt/volume2,
   removed at stop); `metadata()["gate_transfers"]["peak_spool_bytes"]` records its peak. The gate's own upstream timeouts are 8 s to connect and
   4 h to read, so it never fails before the client would. Gate log fields `upstream_bytes`, `t_upstream_done`, `t_first_byte_sent` prove it. `metadata()["gate_transfers"]` gives the per-run
   count of whole-file transfers (`whole_file_transfers`), `upstream_bytes`, `bytes_to_sandbox` and refused Range requests, read from the
   gate log at call time: the source of the D cost figures. D does not force writing to disk (left to the access text); T's quota limits
   disk only, and large in-memory range-read use under T is recorded by the instruments, not prevented.
4. **REST client read timeout** (all of T, T-unpaginated, D, identical): the shipped filesystem passes `timeout=30` to the HTTP
   client, so the filesystem's `timeout` is forced to `(8, 14400)` (4 h read; and the client's module default is raised too), because under D the first byte arrives after the whole file (about an hour for a
   few GB at 10 Mbit/s).
5. **Gate** (policy `gatepolicy.py`): allows five read calls, refuses everything else with 403, logs every request.

## Facts measured on the real federation (#10), reproduced by the mock
- Oneprovider swagger says max `limit` = 1000; the server accepts up to 10,000 and answers HTTP 400 `badValueNotInRange` above.
- The shipped client makes one `/children` request with `limit=1000` and ignores `isLast` / `nextPageToken`:
  under T and D, `ls`/`find`/`glob` silently return the first 1000 entries.

## Slots exposed to the access texts
- `ICSA_DATASET_LOCATION` env var and `metadata()["dataset_location"]`: T, T-unpaginated, D: `<space>/<path>`;
  M, M+: `<mount_path>/<space>/<path>`. S1 = the directory, S2 = the file. Identical across options within a layout.
- `xarray.open_dataset(..., engine="h5netcdf")` works in every option (h5netcdf is pinned in the image).

## Harness API (#8) and instrumentation (#9)
`Sandbox.start(run_key, option, layout, data_config)`, `.exec(code, timeout_s) -> ExecResult(stdout, stderr, exit_code, duration_s, timed_out)`,
`.collect(dest_dir)`, `.metadata()`, `.stop()`. Instrumentation: `$ICSA_INSTRUMENT_MODULE` imported by `sitecustomize` at
interpreter start; traces go to `$ICSA_TRACE_DIR` (`/trace`), copied out by `collect`.

## M: TLS mode
oneclient 25.0 sends no TLS SNI, so site-ay's Traefik serves its self-signed default certificate and verification fails (#10).
**Operator decision, 1 Nov 2026: oneclient runs `--insecure` for the whole campaign**, pilot and calibration included; no certificate
fix is needed for this study. Mitigations: tokens are read-only, dataset-scoped and short-lived; data integrity is checked by sha256 (#3).
- Library default: `DataConfig.oneclient_tls="verify"`; `"insecure"` passes `--insecure`.
- Campaign setting: `icsa.sandbox.config.CAMPAIGN_ONECLIENT_TLS = "insecure"`, applied through `campaign_data_config(**kw)`, which the
  harness (#8) and campaign (#16) use to build the DataConfig of M and M+ runs. It is fixed for the campaign (another value is refused there).
- Recorded per run from the arguments actually passed to the sidecar: `metadata()["oneclient_tls"]` and `["oneclient_args"]`
  (see "oneclient sidecar and TLS verification" below for why the image default had to be neutralised).

## Cache clearing (rationale)
Every run gets a fresh container, a fresh loop disk (new mkfs, so an empty scratch dir), a fresh fsspec instance with no cache
directory, and for M a fresh oneclient process and mount (new inodes: no cached pages carry over from earlier runs).
That clears each cache the issue lists for that run without evicting the caches of concurrent runs, so the host-wide
`drop_caches` is **off by default** (`SandboxConfig.drop_host_caches=True` opts in for single-run measurements, #12).
Evidence per run in `metadata()["cache_clear"]` (empty work/trace dirs and home at start, no fsspec cache) and, for M,
`metadata()["mount_process"]` (start time, host pid, container id of the oneclient process).

## Data provider
The provider host is one value: `DataConfig.provider_hosts` (REST); M uses `oneclient_provider_host`, which defaults to its first entry.

## Limits have no defaults
`Sandbox.start` requires `SandboxConfig(limits=Limits.for_dataset(s1_bytes, s2_bytes))` and refuses otherwise. Validation:
small-option writable storage (work disk + /tmp + trace) below the smaller layout, D disk at least 1.2 x S2 (a lower factor is ignored).

Writable capacity is checked twice: `Limits.validate` models the work filesystem as built (quota x 1.03 + 32 MiB) plus /tmp, trace and
/dev/shm (set with `--shm-size`); after the container starts, `statvfs` inside it measures all four mounts
(`metadata()["writable_capacity_bytes"]`) and the start is refused when the sum could hold the smaller layout (D: work disk >= 1.2 x S2).

## oneclient sidecar and TLS verification
The stock `onedata/oneclient:25.0` image sets `ONECLIENT_INSECURE=1`, which oneclient reads as `--insecure`, so its default entrypoint
runs unverified whatever the flags. The sidecar therefore starts with `--entrypoint env` and `-u ONECLIENT_INSECURE
/opt/oneclient/bin/oneclient -f ...`; `--insecure` is passed only for `oneclient_tls="insecure"`. `metadata()["oneclient_tls"]` is derived from
the arguments actually passed, and `metadata()["oneclient_args"]` lists them (the token goes in the environment and is never recorded).

## Run attribution header (part 2)
The gate adds `X-ICSA-Run: <run_key>` to every upstream request it forwards in T, T-unpaginated and D (lookups, attributes, plain
and merged listings, content, and D's store-and-forward fetches), after dropping any `X-ICSA-Run` the agent sent (any capitalisation),
so a Traefik access log can attribute each REST request to its run although all sandboxes share the host's NAT address. The gate
sits outside the agent container, so the agent cannot remove or forge the value. `run_key` is in `metadata()` and must be 1-200 printable
ASCII characters without spaces (it becomes a header value); `Sandbox.start` refuses anything else.

## Observed I/O mode: what is sampled
`observe_io_mode` reads `org.onedata.access_type` of up to 200 entries of the dataset location (the S1 directory, or the S2 file) through the
sidecar. On site-g the mode is a property of the mount's storage access, not of single files: after one read of S2 the first 200 S1 entries of
the same space already read `proxy` (`test_perf_log_csv_is_collected_and_prefetch_rows_are_distinguishable` reads only S2 in an S1 sandbox and
asserts the mode before `collect`). Before any read everything reads `unknown`, which is recorded as `unknown`; `metadata()` observes again after every new cell.

## M: the sidecar's warnings and errors (per run, in `metadata()`)
The counterpart of the gate's 5xx counts for M, read from OUTSIDE the agent (no M-only code in the agent's interpreter):
`metadata()["sidecar_errors"]` summarises the warnings and errors in oneclient's own log (`/tmp/oneclient/0/oneclient.INFO`, or the perf
log dir): `total`, `by_origin`, `by_kind`, the 20 commonest message `signatures`, `first`/`last` time and `log_lines`; the log itself is
copied to `<run>/oneclient_log/oneclient.INFO` by `collect` (token redacted). `sidecar_error_seen` is true when any was logged and `None`
when the log could not be read (`sidecar_errors` is then `{"unavailable": reason}`: unreadable is unknown, never zero).
Origins, by what the line itself says (the `platform` markers are UNOBSERVED so far: no log of 31 Oct - 1 Nov has a line in which the
provider replies with an error, so that bucket is empty and its marker strings are guesses at oneclient's wording): `sidecar` (the connection to the provider, the storage helper the client builds for direct IO),
`platform` (the line says the Oneprovider answered with an error; none seen so far), `unattributed` (everything else). In particular
`fsOperations.cc: Fuse error exception: <strerror>` is `unattributed`: it names the errno returned to the application but not whether a
local failure or a provider reply caused it. For each such line `fuse_lines` (first 50: `t`, `errno`, `preceded_by`, `gap_s`) and `fuse_preceded_by` (counts) record `preceded_by`, the kind of
the nearest preceding `sidecar` error line within 5 s (null if none): context for the analysis, not a classification, so "EAGAIN right after
a storage-helper failure" is visible without an origin being guessed (Day-0, forced direct IO on site-g: storage helper, then the EAGAIN 0.53 ms later).
`agent_saw_sidecar_error` is `None` (unknown) until the agent's own errno record (the #9 tracer,
the same in every option) is read; it is never inferred from the log.
`fuse_lines` entries also carry `caused_by_agent`: true when the errno is one the agent's OWN request causes whatever the operation
(`ENOENT`, `EROFS`, `EISDIR`: a path that is not there, a write to the read-only mount, a directory opened as a file). The summary counts
them in `fuse_total`, `fuse_caused_by_agent` and `fuse_not_caused_by_agent`; `sidecar_error_seen` ignores them (an error the agent asked
for is not a failure of the data path), and any "the agent saw an error" fallback built on these lines must do the same. Origin stays `unattributed`.
`EACCES` and `EPERM` are deliberately NOT agent-caused: they are the agent's doing on a write or on a path outside the study space, but on a
read inside the study space they mean our read-only token failed or expired (an infrastructure fault that excluding them would hide).
The line `fsOperations.cc:116] Fuse error exception: <strerror>` names neither the operation nor the path, and the neighbouring
`fuseFileHandle.cc: Could not create storage helper for file <id> ...` line gives a file id, not the operation, so a read cannot be told from a
write in the log. They are therefore counted as errors the agent may have seen (the safe direction, it surfaces infrastructure faults) and
marked `ambiguous_permission: true` so the analysis can look at them; the tracer's record (operation and path) decides when it is available.
Still to check on a real log (site-g, after the oracle): that a failed read-ahead block (`ReadCache,prefetch`) which no `read()` asked for
produces no `Fuse error exception` line for the application, or how to tell such a line apart.
