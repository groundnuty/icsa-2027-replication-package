# MODEL, not a measurement: the client read-ahead under detector v2 (#11, amendment 12)

These are the per-instance classes of `OBSERVABILITY.md` (`observable_per_instance`) and the numbers the paper cites next to the live checks in `../2026110*`.

## Files

- **`masking_summary.json`.** Regenerated through the calibration plan's own code path (`icsa/faults/masking.py`):

      uv run python -m icsa.faults.masking --s2 /mnt/volume2/icsa-2027/s2z/sst_s2.nc --seed 20261101 --out results/faults-live/model-readahead-20261101

  It gives, per option and fault, the share of scripted runs that are masked (every omitted day served whole, so unobservable by design) and the share of omitted days served whole. It covers all 50 instances and the calibration instance (I01) alone, with the matrix's replicate counts.
- **`s2_chunk_index.csv.gz`.** The S2 chunk index (day, start, end), from the S2 file whose sha256 and size are recorded in the summary.
- **`v2model.py` and `v2model.json`.** The first, independent reading (a scratch script). It also gives detector v1's recall, and agrees with `masking.py` on every v2 share.

## Inputs

- Each client is taken as observed live:
  - **T:** fsspec 2026.9.0's `ReadAheadCache`, with a 5 MiB block and one `fs.open` per file per run.
  - **M:** the application's offset is kept and the size is rounded up to 4 KiB pages.
  - **D:** whole files.
- The real `make_scenario`, `injection`, `read_plan` and `script.execute`.
- Detector v2's coverage rule.

The live checks agree with the model for both T and M: `tests/faults/test_masking.py` compares the model with the logged Range and with the `FsLogic` rows.

## Results (seed 20261101)

| fault (S2, T Traefik) | runs masked | omitted days served whole |
|---|---|---|
| `chunk_skip` | 12.5% | 91.7% |
| `chunk_range_skip` | 0% | 2.9% |
| `header_only` | 0% | 41.5% |
| `baseline_dropped`, `target_dropped`, `wrong_period` | 0% | 0% |

Every M fault: 0% masked and 0% served.

## Calibration

The calibration's own verdicts are computed per planned run by `matrix.calibration_plan` (`seal_masking`), from its master seed, the calibration instance's required set and this chunk index. They are sealed into the claimed plan's sha before any run.
