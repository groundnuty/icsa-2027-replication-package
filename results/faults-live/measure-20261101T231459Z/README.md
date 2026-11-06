# Raw-read timing, S2, 1 Nov 2026 23:14:22-23:17:13Z (#11 part 2)

`calibrate measure --layout S2 --n 100` at acaf03c, on image icsa-sandbox:11cal-acaf03c, with slot users T-1, D-1 and M-1, one sandbox at a time.

- **T and M:** I01's first 100 required chunks, read through one open file each.
- **D:** one whole-file download (3,785,412,176 B), which is what a calibration D run does in S2.

| option | sandbox start | read |
|---|---|---|
| T | 8.1 s | 1.54 s for 100 chunks (5 MiB read-ahead) |
| D | 8.0 s | 76.5 s for the one download |
| M | 8.5 s | 5.99 s for 100 chunks, about 5.6 s of it the per-mount storage detection |
