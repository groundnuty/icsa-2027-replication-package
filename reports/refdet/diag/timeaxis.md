# Time axis versus initialisation (issue #4)

Script: `tools/diag/diag_timeaxis.py`. No thresholds: the rebuilt authors' SST is compared with our raw SST directly.

## 1a. Time coordinates

- BALMHW_supp.nc time: [1.0, 2.0, 3.0] .. [366.0]; units '1: January 1st, 2: January 2nd, ..., 60: February 29th, ..., 366: December 31st'
- raw SST_BAL_1982.nc time: [31536000, 31622400, 31708800] 'seconds since 1981-01-01', calendar 'proleptic_gregorian' -> ['1982-01-01T00:00:00', '1982-01-02T00:00:00', '1982-01-03T00:00:00']; global time_coverage_start '20241231T000000Z', time_coverage_end '20250101T000000Z'
- BALMHW_event_001.nc time: [378820800.0, 378907200.0, 378993600.0] 'seconds since 1970-01-01 00:00:00', calendar 'gregorian' -> ['1982-01-02T12:00:00', '1982-01-03T12:00:00', '1982-01-04T12:00:00']
- The authors' code builds these labels itself and does not read them from their SST files:
  - Step_2: `time=datenum(1982,1,1):datenum(2023,12,31)`, with SST_reshaped's third index taken as that day;
  - Step_4: `mhw_time=datetime(1982,1,2,12,0,0):days(1):datetime(2023,12,30,12,0,0)`.
- So a label offset in the authors' data cannot be seen in the published time coordinates. It can only be seen in the values.

## 1b. Shift -1 against shift 0, every verified event, all days, MHW cell-days

Verified event files on disk: 15 of 189.

| event | first day (authors) | days | cell-days | exact at shift 0 | mean abs d at 0 (K) | exact at shift -1 | mean abs d at -1 (K) |
|---|---|---|---|---|---|---|---|
| 001 | 1982-01-02 | 7 | 1324 | 0.007 | 0.083 | 0.428 | 0.009 |
| 002 | 1982-03-30 | 8 | 1614 | 0.045 | 0.098 | 0.014 | 0.301 |
| 003 | 1982-04-18 | 11 | 4898 | 0.019 | 0.280 | 0.012 | 0.660 |
| 004 | 1982-05-26 | 5 | 5 | 0.000 | 0.126 | 0.000 | 0.486 |
| 005 | 1982-06-01 | 13 | 46846 | 0.008 | 0.534 | 0.005 | 1.106 |
| 006 | 1982-07-12 | 33 | 91461 | 0.016 | 0.232 | 0.010 | 0.436 |
| 009 | 1983-09-06 | 6 | 879 | 0.000 | 0.269 | 0.000 | 0.358 |
| 010 | 1983-09-23 | 5 | 50 | 0.000 | 0.105 | 0.000 | 0.151 |
| 017 | 1985-06-03 | 8 | 2765 | 0.002 | 0.795 | 0.002 | 0.926 |
| 018 | 1985-08-19 | 8 | 1601 | 0.004 | 0.604 | 0.007 | 0.628 |
| 020 | 1986-05-04 | 10 | 707 | 0.000 | 0.894 | 0.000 | 1.436 |
| 021 | 1986-06-16 | 5 | 15 | 0.000 | 0.356 | 0.000 | 1.056 |
| 024 | 1987-10-25 | 11 | 5597 | 0.011 | 0.114 | 0.015 | 0.129 |
| 029 | 1988-10-02 | 5 | 5 | 0.000 | 0.092 | 0.000 | 0.088 |
| 034 | 1989-07-26 | 5 | 80 | 0.000 | 0.111 | 0.013 | 0.409 |

All verified events together: exact at shift 0 2129/157847 = 0.0135, mean abs d 0.333 K; exact at shift -1 1876/157847 = 0.0119, mean abs d 0.641 K.

## 2. Decay at the start of the record (authors' labels 1982-01-02..1982-01-14, rebuilt cells only)

| authors' day | rebuilt cells | exact vs our previous day (shift -1) | exact vs our same day (shift 0) |
|---|---|---|---|
| 1982-01-02 | 205 | 205/205 = 1.000 | 0/205 = 0.000 |
| 1982-01-03 | 232 | 135/232 = 0.582 | 0/232 = 0.000 |
| 1982-01-04 | 232 | 98/232 = 0.422 | 0/232 = 0.000 |
| 1982-01-05 | 232 | 54/232 = 0.233 | 2/232 = 0.009 |
| 1982-01-06 | 232 | 32/232 = 0.138 | 5/232 = 0.022 |
| 1982-01-07 | 184 | 43/184 = 0.234 | 2/184 = 0.011 |
| 1982-01-08 | 7 | 0/7 = 0.000 | 0/7 = 0.000 |
| 1982-01-09 | 0 (no published MHW cell on this day) | n/a | n/a |
| 1982-01-10 | 0 (no published MHW cell on this day) | n/a | n/a |
| 1982-01-11 | 0 (no published MHW cell on this day) | n/a | n/a |
| 1982-01-12 | 0 (no published MHW cell on this day) | n/a | n/a |
| 1982-01-13 | 0 (no published MHW cell on this day) | n/a | n/a |
| 1982-01-14 | 0 (no published MHW cell on this day) | n/a | n/a |

Cells where both are finite cannot be compared outside MHW cell-days: the authors' SST is published only there.
