# Live check, part 2: prefetch_on and the S2 header reads, 1 Nov 2026 21:41:37–21:43:14Z (#11, science's amendment 12)

**What ran.** `python -m icsa.faults.live_check --only Mpre,T2h,M2h --prefetch-args "--read-buffer-prefetch-duration 10"` at 864ec7b, on the same image and config as `../20261101T212027Z`. Leases: M-1 (`8f3e857b…8ddc`) for Mpre and M2h, T-1 (`3621f404…589b`) for T2h. Only our own lines are kept: 295 audit lines and 6 Traefik lines.

**prefetch_on with 10 s: SUPERSEDED.** Science froze prefetch_on at 30 s with a 1 GiB buffer (#11, 21:40Z); that run is in `../20261101T220413Z`. This one is kept for the record.

**prefetch_on as first relayed.**
- **Flags:** `--read-buffer-prefetch-duration 10` (ten times the default of 1). Every other read-buffer setting stays at its default. The default `--read-buffer-max-size` is 104,857,600 B, larger than any S1 file (169–212 KB), so nothing else was set. Calibration does NOT use these: it uses the frozen flags in `../20261101T220413Z`.
- **Full read of `sst_19820109.nc` through xarray.**
  - Audit: `open_file`, then 30 × `remote_read`, then `fsync` and `release`.
  - Perf: 37 `FsLogic,read` rows over [0,211015) and 30 `ReadCache,prefetch` rows.
- **Header read of `sst_19820110.nc`, 15,241 B.**
  - Audit: `open_file`, then 3 × `remote_read`.
  - Perf: `FsLogic,read` covers [0,16384).
- **Result:** both reads leave the same lines as their cold counterparts in `../20261101T212027Z`.

**S2 header reads, bytes [0, 89079).** The first chunk is day 0 (1982-01-01), at [89079, 248429).
- **T.**
  - Traefik: `GET …/content`, 206, `Range: bytes=0-5331958`, 5,331,959 B. That is the 89,079 bytes asked, plus one 5 MiB fsspec block read ahead.
  - Audit: one `open_file_with_extended_info`, `synchronize_block`, one `remote_read` and `release`.
- **M.**
  - Perf: `FsLogic,read` covers [0,90112), 1,033 B into chunk 0.
  - Audit: `open_file`, 3 × `remote_read`, `fsync` and `release`, plus one more `remote_read` 17 ms after `release` (read-ahead completing).
- **Result:** the bytes past the header fall in early-1982 chunks, which no instance ever requires (the baseline starts in 1992).
