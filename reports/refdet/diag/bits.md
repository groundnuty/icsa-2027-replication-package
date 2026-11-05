# Bit comparison of the published anomalies with our SST (issue #4)

> Reading: the low uint32 shares are consistent with MATLAB having subtracted the unpublished double climatology, which would make the anomaly bits differ even for identical SST. This is an inference, not shown. The SST-level test in the last table is the direct one.

Script: `tools/diag/diag_bits.py`. Prediction: `float32(our_sst32 - mclim32)` against `MHW_int_maps`, compared as uint32, on every published MHW cell-day.

Checksum-verified event files: 15 of 189.

| event | first day (authors) | cell-days | shift 0: bit-equal / within 1 ulp | shift -1: bit-equal / within 1 ulp |
|---|---|---|---|---|
| 002 | 1982-03-30 | 1614 | 5/1614 = 0.003 / 0.003 | 2/1614 = 0.001 / 0.001 |
| 001 | 1982-01-02 | 1324 | 0/1324 = 0.000 / 0.000 | 16/1324 = 0.012 / 0.012 |
| 003 | 1982-04-18 | 4898 | 2/4898 = 0.000 / 0.000 | 1/4898 = 0.000 / 0.000 |
| 004 | 1982-05-26 | 5 | 0/5 = 0.000 / 0.000 | 0/5 = 0.000 / 0.000 |
| 005 | 1982-06-01 | 46846 | 8/46846 = 0.000 / 0.000 | 8/46846 = 0.000 / 0.000 |
| 006 | 1982-07-12 | 91461 | 53/91461 = 0.001 / 0.001 | 27/91461 = 0.000 / 0.000 |
| 009 | 1983-09-06 | 879 | 0/879 = 0.000 / 0.000 | 0/879 = 0.000 / 0.000 |
| 010 | 1983-09-23 | 50 | 0/50 = 0.000 / 0.000 | 0/50 = 0.000 / 0.000 |
| 017 | 1985-06-03 | 2765 | 0/2765 = 0.000 / 0.000 | 0/2765 = 0.000 / 0.000 |
| 018 | 1985-08-19 | 1601 | 0/1601 = 0.000 / 0.000 | 0/1601 = 0.000 / 0.000 |
| 020 | 1986-05-04 | 707 | 0/707 = 0.000 / 0.000 | 0/707 = 0.000 / 0.000 |
| 021 | 1986-06-16 | 15 | 0/15 = 0.000 / 0.000 | 0/15 = 0.000 / 0.000 |
| 024 | 1987-10-25 | 5597 | 5/5597 = 0.001 / 0.001 | 4/5597 = 0.001 / 0.001 |
| 029 | 1988-10-02 | 5 | 0/5 = 0.000 / 0.000 | 0/5 = 0.000 / 0.000 |
| 034 | 1989-07-26 | 80 | 0/80 = 0.000 / 0.000 | 0/80 = 0.000 / 0.000 |

All: shift 0 bit-equal 73/157847 = 0.0005, within 1 ulp 0.0005; shift -1 bit-equal 58/157847 = 0.0004, within 1 ulp 0.0004.

## First days of the record (authors' labels)

| authors' day | cell-days | anomaly, shift -1: bit-equal / within 1 ulp | anomaly, shift 0: bit-equal / within 1 ulp | SST vs our previous day: max abs d (K) / share within half an ulp at 280 K / share differing by at least 0.005 K |
|---|---|---|---|---|
| 1982-01-02 | 205 | 3 / 3 | 0 / 0 | 1.48e-05 / 1.000 / 0.000 |
| 1982-01-03 | 232 | 4 / 4 | 0 / 0 | 0.06 / 0.582 / 0.418 |
| 1982-01-04 | 232 | 5 / 5 | 0 / 0 | 0.06 / 0.422 / 0.578 |
| 1982-01-05 | 232 | 4 / 4 | 0 / 0 | 0.06 / 0.233 / 0.767 |
| 1982-01-06 | 232 | 0 / 0 | 0 / 0 | 0.06 / 0.138 / 0.862 |
| 1982-01-07 | 184 | 0 / 0 | 0 / 0 | 0.07 / 0.234 / 0.766 |
| 1982-01-08 | 7 | 0 / 0 | 0 / 0 | 0.03 / 0.000 / 1.000 |
