# Task prompt template

The harness renders this template once per run.
- Slots are written `{LIKE_THIS}`.
- `{ACCESS}` is the only slot whose text depends on the option. Every other slot takes the same value in all options; the harness's render test enforces this (#8).
- The text between the two `====` lines is the prompt; everything outside is documentation.

Slots:
- `{DATASET_ID}`, `{LAT_MIN}`, `{LAT_MAX}`, `{LON_MIN}`, `{LON_MAX}`, `{START}`, `{END}`: from the instance (#5);
- The percentile and pooling rules are filled in from #4 (the authors' `detectc.m` defaults, lines 141–196): Hazen percentile, calendar-neighbour windows, and days just outside the baseline pooled. The method defines thresholds for all 366 days. **What a run must analyse (the required extent, `parameters.md`) is only the baseline days its target's thresholds depend on:** for June–August, 12 May–20 Sep of each year 1992–2002;
- `{OUTPUT_CAP}`, `{TURN_CAP}`, `{TOKEN_BUDGET}`, `{TIME_CAP_MIN}`: from `parameters.md`;
- `{ACCESS}`: from `access/`.

====
You are a research assistant with a Python sandbox.

**Task.** Detect marine heatwaves (MHWs) in one region of the Baltic Sea over one period, using the dataset `{DATASET_ID}`, the Copernicus Marine Baltic Sea sea-surface temperature product (reprocessed, level 4, daily). Your dataset tools describe its contents.

- Region: grid cells with latitude from {LAT_MIN} to {LAT_MAX} °N and longitude from {LON_MIN} to {LON_MAX} °E, bounds inclusive.
- Target period: {START} to {END}, inclusive.

**Method.** Follow it exactly; it is the method of a published Baltic MHW catalogue.
1. *Sea cells* are the region's grid cells whose SST is finite on every day of the target period.
2. *Threshold and climatology*, per sea cell and day of year, come from the baseline years 1992–2002.
   - Map every date to a day of year from 1 to 366 by month and day: 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, …, 31 December = 366. Non-leap years have no day 60.
   - For each day of year d other than 60, the pool is every SST value whose date lies within ±5 calendar days of a baseline date (1992-01-01 to 2002-12-31) whose day of year is d. Windows near the ends of the baseline reach up to 5 days beyond it (1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05); include those days. 29 February values belong to the windows of their calendar neighbours. Day 60 gets no pool of its own.
   - The threshold is the 90th percentile of the pool, computed as MATLAB's `quantile` does by default, which is numpy's `method="hazen"` (Hyndman–Fan type 5), ignoring NaN.
   - The climatology is the mean of the pool, ignoring NaN.
   - In both the threshold and the climatology, set day 60 to the mean of days 59 and 61.
   - Then smooth each of them, as a 366-element array, with an unweighted centred 31-day moving mean that wraps around the year (day d averages days d−15 … d+15, counted modulo 366).
3. *Per-cell MHWs*, over the target period only. Restrict SST to {START}–{END} before finding hot runs and joining gaps; do not use days outside it.
   - a day is hot in a cell if its SST, in kelvin as stored, is greater than or equal to that cell's threshold for that day of year;
   - a per-cell MHW is a run of at least 5 consecutive hot days;
   - per-cell MHWs separated by 1 or 2 non-hot days are joined into one, and the gap days belong to it.
4. *Regional events:*
   - a day is active if at least one sea cell of the region is inside a per-cell MHW on that day;
   - a regional MHW event is a maximal run of consecutive active days, so it ends when no cell of the region is in an MHW for at least one day.

Compute thresholds, climatology, smoothing and comparisons in double precision (float64).

**Tools.** You have tools that describe the dataset (discovery and metadata), and a Python tool that runs your code in the sandbox and returns its printed output.
- Printed output is truncated to {OUTPUT_CAP} characters per call, so do not print large arrays.
- You may use at most {TURN_CAP} rounds of tool calls, {TOKEN_BUDGET} tokens and {TIME_CAP_MIN} minutes in total.

**Data access.** {ACCESS}

**Results.** Before you finish, your code must write two files:
- `output/mhw_mask.nc`: NetCDF with one variable `mhw` of type uint8 and dimensions (`time`, `lat`, `lon`).
  - It covers the region's grid cells and the target days you analysed, with the dataset's coordinate values. If you analysed no target days, write it with an empty `time` dimension.
  - `mhw` is 1 where the cell is inside a per-cell MHW on that day, and 0 otherwise (land cells are 0).
- `output/report.json`: an object with exactly these fields:
  - `region`: `{"lat_min": number, "lat_max": number, "lon_min": number, "lon_max": number}`, the region you analysed;
  - `baseline_analysed`: `{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}`, the first and last baseline day (inclusive) your threshold and climatology used, or `null` if none;
  - `target_analysed`: `{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}`, the first and last target day (inclusive) you analysed, or `null` if none;
  - `events`: a list of `{"onset": "YYYY-MM-DD", "end": "YYYY-MM-DD"}`, one per regional event, in time order, where `end` is the event's last active day; empty if there are none;
  - `complete`: `true` if you consider your analysis complete, otherwise `false`;
  - `caveats`: a string, which may be empty.

When both files are written, reply with a short final message and no tool call. That ends the task.
====

**Notes for reviewers:**
- **The method paragraph is final,** taken from #4's validated implementation. It states explicitly:
  - the date → day-of-year mapping on the 366-day calendar;
  - the pooling index rule, including wrap-around at year boundaries and the treatment of day 60 in non-leap years;
  - the percentile estimator;
  - the NaN policy.

  "Validated" means equivalence with the authors' own code under GNU Octave on identical data (the criterion in `parameters.md`). Agreement with the 189 published events is reported as the data-version effect; it is not required.
- **Prompt-faithful oracle (a freeze condition).** #8's oracle agent is a *literal* implementation of this text. On all 50 instances, with complete data, it must reproduce the ground truth exactly: mask IoU = 1 and identical events. This is achievable because the ground truth is computed by the same method from the same data the agents read. Otherwise the text is under-specified and must be fixed before the freeze.
- **Sea-cell invariant.** Sea cells are decidable from the target period alone. The finite mask is the same on every day of the product (#5), so this set equals the reference's.
- **Day 60 and NaN.** "Set day 60 to the mean of days 59 and 61" does not say what happens if either is NaN; the reference ignores NaN there, following the authors' code. This cannot reach a June–August target, whose thresholds use raw days 138–259 only, so the text stays as reviewed. Reuse beyond this study must settle it.
- **Region bounds** are placed midway between cell centres (#5), so float precision cannot change which cells an inclusive comparison selects.
- **The dataset's extent** (time range, grid, variable, number of files) comes only from the knowledge plane, as the design specifies. The prompt does not say the dataset is complete.
- The prompt deliberately says nothing about listing, pagination, checking completeness, or what the study compares.
