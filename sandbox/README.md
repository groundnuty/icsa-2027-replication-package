# Sandbox (#7): enforced data paths

One image (`sandbox/Dockerfile`, pinned `requirements.txt`), one Python API
(`icsa.sandbox`), five options. Build: `docker build -f sandbox/Dockerfile -t icsa-sandbox:<tag> . (the tests derive the tag from a hash of the build context)`
(from the repo root; `docker` and passwordless `sudo` for loop mounts are needed).

## Python API (for the harness, #8)

```python
from icsa.sandbox import Sandbox, SandboxConfig, DataConfig
sbx = Sandbox.start(run_key, Option.T, Layout.S1, DataConfig(onezone_host=..., space_name=..., token=...))
res = sbx.exec("print(1)", timeout_s=600)   # ExecResult(stdout, stderr, exit_code, duration_s, timed_out)
sbx.collect(dest_dir)                       # output/report.json, output/mhw_mask.nc, cells/, trace/, gate_requests.jsonl
sbx.metadata()                              # RunRecord.sandbox
sbx.stop()                                  # or: with Sandbox.start(...) as sbx:
```

Files in `/work` (home and cwd of the unprivileged user, uid 10001) persist between `exec` calls
of one run. The agent writes `/work/output/report.json` and `/work/output/mhw_mask.nc`.

## What each option allows, and how it is enforced

Every run gets a loop-mounted ext4 disk (the quota, ENOSPC beyond it), an **internal** docker
network with no route out, and a **gate** container that is the agent container's only network
peer. The agent container: read-only root, all capabilities dropped, `no-new-privileges`, fixed
`--cpus/--memory/--pids-limit`. Sandboxes live under `ICSA_DATA/sandboxes` (`/mnt/volume2`).

The gate (`icsa/sandbox/gate.py`, policy in `gatepolicy.py`) answers the Onedata host names
(via `--add-host`) with TLS certificates of a per-run CA that only the sandbox trusts, applies the
policy, and forwards to the real Onezone/Oneprovider (certificates verified). Everything not
listed is refused with 403, and one JSON line per request is logged (`gate_requests.jsonl`).

| Option | Path | Enforcement |
|---|---|---|
| T | official fsspec REST client, range reads | gate allows lookup, attrs, `children`, `content` (with or without Range). Disk = small quota (`Limits.small_disk_bytes`, placeholder 5 GiB). No FUSE device, no capabilities, no route to a mount. A whole-file download is not blocked by a heuristic; it dies at the quota (ENOSPC) and the instruments record it. |
| T-unpaginated | T, except the listing is complete | **Only difference:** for `GET /data/{id}/children` the gate follows `nextPageToken` upstream (pages of `page_limit`=1000) and answers with one page with `isLast: true`. Works whether or not the API caps the page size, so it does not depend on #10 question 3. Applies to `ls`, `find`, `glob` alike. |
| D | same client and token, whole-file download only | same as T, plus the gate refuses any `content` request that carries a `Range` header (403). `cat_file(path)` without bounds works (whole download); `cat_file(path, start, end)`, `fs.open(...).read(n)` and raw `Range:` requests fail. Disk = max(`d_disk_bytes`, 1.2 x `s2_size_bytes`). |
| M | oneclient FUSE mount at `/data`, read-only, no REST token | The agent container has **no route to any Onedata host** (the gate serves no Onedata name for M), no FUSE device and no token. A **sidecar** container (`onedata/oneclient:25.0`) holds the token and the FUSE mount and exports it to `/data` of the agent container read-only by bind propagation (`rshared` to `rslave`). |
| M+ | as M | The same, after `DataConfig.replicate()` (the scripted replication of #12) ran. Scripted measurements only. |

**Known properties of D** (not bugs; the D access text must say so):
- the shipped `fs.get()`/`get_file()` read in ranges and would be refused; the D shim above replaces `get_file`;
- unbounded `cat_file(path)` downloads, but holds the whole body in RAM (it returns `response.content`): S2
  does not necessarily fit the RAM limit. A file bigger than RAM is downloaded with the client's streaming call,
  `fs.client.iter_file_content(space, file_path=...)` (no Range header, `stream=True`), written to `/work`
  (the D shim's `fs.get` does exactly this, so `fs.get` also copes with files bigger than RAM);
  `test_d_downloads_a_file_larger_than_ram_by_streaming` shows both (256 MiB RAM, 700 MB file);
- stream-and-abort is closed by **store-and-forward** at the gate (see INTERFACE.md): a range-less `GET` of a content
  is fetched whole from the provider before the sandbox receives any byte, so reading 1 KB of it and closing still
  costs one complete transfer, whatever the client call (`requests`, `fs.client.iter_file_content`, `fs.get`);
- a refused Range read answers HTTP **400** with a message, not 403, because the shipped client's 403
  path raises an unrelated `TypeError` (it calls `len()` on the empty request body while logging).

**Network:** the sandbox network is `--internal` and created with `inhibit_ipv4`, so the host has no
address on it. Without that option a container on an internal network can still reach every service
the host listens on via the bridge gateway (found by `test_agent_cannot_reach_the_host_around_the_gate`).

**Download URLs:** the gate only allows the five calls in `gatepolicy.py`; `/download/...`, `/cdmi/...`,
metadata and anything else answer 403 (tested with candidate paths). The exact Onedata 25 download-URL
endpoint could not be confirmed from the docs here; check it against the real Oneprovider.

**Known property of the shipped client** (verified by reading onedatarestfsspec 25.0.0 `core.py`):
`OnedataFileSystem.ls` calls `list_children` once with the client's default `limit=1000` and never
follows `nextPageToken`; so in T and D `ls`/`find`/`glob` return at most the first 1000 entries of a
directory, silently. The 1000 is a client default, not an API cap; whether the API accepts larger
pages is #10 question 3 and is not needed here.

## Interface specification: what is shipped and what was written for this study

Everything in a data path is the shipped Onedata client (onedatarestfsspec 25.0.0 +
onedatafilerestclient 25.0.0, matching the federation; 25.2.0 behaves the same) **except**:

1. **T-unpaginated listing shim** (`gate.py`, `_merged_listing`). Wraps only the listing call
   (`GET /data/{id}/children`): the gate requests pages of 1000 (`page_limit`) and follows `nextPageToken`
   until `isLast`, then answers the client with one page, all entries, `isLast: true`. Reads are identical to T.
   It sits in the gate, not in the client, so `ls`, `find`, `glob`, `walk`, `du` all see the full listing.
   T and D list exactly as shipped.
2. **D client conveniences** (`sandbox/hooks/icsa_option_shims.py`, D only, not enforcement): any in-place
   remote read (`fs.open(...).read()`, `cat_file(start/end)`, xarray on a remote file object) raises at once,
   without a request, with: *"In this sandbox, files cannot be read remotely in place; download whole files
   with fs.get(remote_path, local_path) first."*; `fs.get(remote, local)` streams the whole file (the shipped
   `get_file` reads through `open()` in ranges). The gate refuses `Range` on content for D regardless
   (HTTP 400, same message), so the shim is not what enforces D.

Documentation mismatches, recorded as facts (measured on the real federation, #10):
- the Oneprovider swagger gives max `limit` = 1000; the server accepts up to 10,000 and answers HTTP 400
  `badValueNotInRange` above that (no clamping);
- the shipped client ignores `isLast` / `nextPageToken` (25.0.0 and 25.2.0): `ls`, `find`, `glob`, `walk`, `du`
  return the first 1000 entries only. The mock reproduces both.

**Dataset location** per layout is `ICSA_DATASET_LOCATION` in the container and
`metadata()["dataset_location"]`: T, T-unpaginated, D: `<space>/<path>` for the client; M, M+:
`<mount_path>/<space>/<path>`. S1 = the directory (`DataConfig.s1_path`), S2 = the file (`s2_path`); both are
placeholders until #3 fixes the layout.

## Caches cleared at start (recorded in `metadata()['cache_clear']`)

Fresh container; fresh loop disk (new `mkfs`); empty `/trace`; no fsspec cache dir
(`FSSPEC_CONFIG_DIR` points nowhere, HOME is the empty disk); host page cache dropped
only when `drop_host_caches` is set (opt-in); M: a fresh
oneclient sidecar (empty tmpfs for its state) and a fresh mount.

## Instrumentation slot (for #9)

At every interpreter start `sitecustomize` imports `$ICSA_INSTRUMENT_MODULE` (default
`icsa_noop_instrument`, a no-op). To supply a module: put it in a directory and pass
`SandboxConfig(instruments_dir=<dir>, instrument_module="<name>")`; it is mounted read-only at
`/opt/icsa/instruments` and put first on `PYTHONPATH`. It may write under `$ICSA_TRACE_DIR`
(`/trace`, a 256 MiB tmpfs); `collect` copies `/trace` out. An import error does not break the
agent's code; it is written to `/trace/instrument-error.log`.

A `.pth` line in site-packages imports `icsa_site_boot` in every interpreter. With the instruments
directory mounted, it loads the instrument even if the environment has been scrubbed (`env={}`,
`python -I`, `-E`); without that directory it does nothing. Only `python -S` gets past it, and its
launch is on record (`icsa/instruments/DESIGN.md`, Blind spots).

## Tests

`uv run pytest -q tests/sandbox` (pure policy tests need no docker; the rest need docker + sudo and
a local mock, `icsa/sandbox/mock_onedata.py`, which implements the REST calls the client makes).

Not testable without the federation (waiting for Onedata, #3/#1):
- M with the real `oneclient`: the FUSE mount propagating through the bind, `-o ro,allow_other`,
  `--force-direct-io/--force-proxy-io`, listing and reads. The local M tests use a plain directory as a
  **stand-in** mount (`DataConfig.mount_stub_dir`, recorded as `mount_kind: stub-dir (TEST ONLY)`);
  they prove the agent-side plumbing (read-only, no REST, no token), not oneclient.
- M: that the oneclient token is unobtainable from the sandbox: attempt REST with whatever the sandbox can reach (no local test: the stand-in mount never holds a token, so a scan would prove nothing).
- Negative T "mount": with the real federation, attempt `oneclient` inside the T sandbox.
- All of T/D against the real site-ay Onezone/Oneprovider TLS and the real `children` response shape
  (`nextPageToken`/`isLast` field names are taken from the client's `ListChildrenResult`).
- Positive test against the #3 checksums, including S2 ranges and real oneclient M and M+ (the local M test reads 50 days from a stand-in directory; M+ is only tested to refuse a start without the replication callback). The oneclient sidecar has the same cpu/memory/pids limits as the agent; its writable-layer disk is not capped (it holds only a tmpfs cache of 1 GiB and no data).

## Knowledge plane
`DataConfig.knowledge=[{"name","host","port"}]`: each name resolves to the gate, which forwards plain TCP
(TLS end to end) on that port; ports are unique and not 443. **Not tested against a real knowledge
plane** (none is specified yet) and no TLS-by-hostname routing on 443.

## Design questions (also in the final report)
- `drop_host_caches` (host-wide `drop_caches` before a run) is off by default, because it evicts other runs' caches;
  per-run freshness is by new container/disk/mount (see INTERFACE.md). Opt in for single-run measurements.
- D: how does an agent download a file larger than RAM (see above)? The D access text depends on it.

## Disk sizes follow the real data
S1/S2 are deflate level 4 (no shuffle), S2 about 3-4 GB. Build the limits from the real sizes:
`Limits.for_dataset(s1_bytes, s2_bytes)` gives D disk = 1.2 x S2 and writable storage (work disk, /tmp, trace) of at most half the smaller layout, so
a wholesale copy cannot fit. There are no default sizes or quota: `Sandbox.start` refuses a missing `SandboxConfig.limits` and limits whose small-option writable storage (work disk + /tmp + trace) could hold a wholesale copy of the smaller layout.

## Placeholders to confirm with the science agent
CPU/RAM (4 cpus, 16 GiB), the small quota (5 GiB), the S2 size (`NDAYS*NLAT*NLON*4`, replace by the
real file), the output size limit inside the small quota.

## Image pinning
`SandboxConfig.image` is a reference (tag or id) and `pinned_image_id` the immutable id it must resolve to; there is no default tag.
A campaign calls `icsa.sandbox.pin_image(tag)` once at its start, stores the id in its state and puts it in every `SandboxConfig`;
`Sandbox.start` refuses when `image` no longer resolves to the pinned id (a rebuild or retag by another branch or session) and starts every
container by the resolved id. The tests build `icsa-sandbox:test-<hash of the build context>` and run everything by the id they resolved.
The oneclient sidecar image is recorded (`oneclient_image_id`) but not pinned.
