# Raw-read timing of the calibration runner, 1 Nov 2026, 23:09:54–23:11:39Z (#11 part 2; the parent's GO at 23:10Z)

**What ran.** `python -m icsa.faults.calibrate measure --n 100` at d84044c, on image `icsa-sandbox:11cal-d84044c` built from that head.
- **The read code:** `execute_run`, the calibration's own path: the real sandbox, a slot-user lease (T-1, D-1, M-1) and the quarantine rule. One sandbox at a time.
- **The files:** the first 100 of I01's required S1 files, 32.7 MB, each read whole.
  - T: one `fs.open` per file.
  - D: `fs.get`.
  - M: the mount.
- **Run keys:** `s11cal-measure-{T,D,M}-230954`.
- **Host load:** about 20.

| option | sandbox start | read of 100 files | per file |
|---|---|---|---|
| T | 9.3 s | 10.1 s | 0.101 s |
| D | 7.6 s | 10.0 s | 0.100 s |
| M | 9.6 s | 10.4 s | 0.104 s |

M's time includes oneclient's once-per-mount storage detection, about 5.6 s (`results/m-throughput/NOTES.md`).

These numbers replace the smoke runs' full-instance walls in the calibration's site-g-time estimate. The smoke runs included the detector's compute and ran at a load of about 40.
