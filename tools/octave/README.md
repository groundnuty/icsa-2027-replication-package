# Authors' detectc.m under GNU Octave (equivalence check for #4)

Octave 9.2.0, image `gnuoctave/octave:9.2.0`, always `--network none`, code and inputs mounted read-only.

- `prepare.sh <work>`: builds the work dir. It writes m_mhw `detectc.m` patched with `detectc_octave.patch` (the downloaded original is never edited), plus the shims and the runner, and records sha256s in `PROVENANCE`.
- The patch replaces only what Octave lacks:
  - `internal.stats.parseArgs/getParamVal` becomes the defaults (Step_2 passes no options);
  - `datetime/day` becomes a datenum day of year in the leap year 2012/2000, as the original;
  - `string()` becomes arithmetic on `datevec`;
  - `smoothdata(...,'movmean',31)` becomes `movmean_omitnan.m`, because Octave's movmean has no 'omitnan'. smoothdata's default is omitnan with shrinking ends.
- `nanmax.m` and `nansum.m` are shims for functions core Octave lacks.
- `t_semantics.m`: hand-computed checks of Octave's `quantile` and of the movmean shim (log in `reports/refdet/diag/octave_semantics.log`: 15/15 pass), plus the precision facts below.
  - Octave's default `quantile` is method 5, as MATLAB's: NaN ignored, clamped at both ends.
  - On single SST, `quantile` and `mean` return single; `m90`/`mclim` are kept in double through smoothing.
  - A single-vs-double comparison is made in single in Octave (`single(0.1) == 0.1` is true). MATLAB's rule is unverified (no licence).
- One block:
  - `make_input.py <block> lat0 lon0 h w y0 y1 [s1|raw]` writes `in/sst.bin`, `in/meta.txt` and `in/source.json` (sha256).
  - Then run:

        docker run --rm --network none -v <work>:/work:ro -v <block>/in:/in:ro -v <block>/out:/out gnuoctave/octave:9.2.0 octave-cli --eval "run('/work/run_block.m')"

  - Then `compare_block.py <block>` writes `out/compare.json`.
- `make_nan_block.py` derives a block with NaN injected deterministically. It covers the NaN paths, which real 202506 baseline data never take.
- `run_tiny.m`, `t_mm.m`: the first smoke tests from 31 Oct, kept for the record.
