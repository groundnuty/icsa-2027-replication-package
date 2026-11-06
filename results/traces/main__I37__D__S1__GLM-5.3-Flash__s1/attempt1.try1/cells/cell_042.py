import json, datetime as dt
import numpy as np

report = {
    "region": {"lat_min": 60.09, "lat_max": 61.29, "lon_min": 20.01, "lon_max": 21.21},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2012-06-01", "end": "2012-08-31"},
    "events": [],
    "complete": True,
    "caveats": (
        "No regional MHW events were detected: in the period 2012-06-01..2012-08-31 the regional daily mean "
        "SST anomaly relative to the 1992-2002 climatology reached only about +2.1 K (max on 2012-08-18), while "
        "the smoothed 90th-percentile thresholds sit roughly 3 K above the climatology in late summer. Only 7 "
        "individual cell-days anywhere in the region reached the threshold (2012-08-17..19, five cells around "
        "60.35N/21.1E), the longest run of consecutive hot days in any single cell was 3 days (< the 5-day "
        "minimum), so no per-cell MHW exists, no day is active, and the mask is all zeros. All 3370 sea cells "
        "had finite SST on every target day. Baseline pools for every day of year (except 29 Feb, which has no "
        "pool of its own) were complete: 113-121 values per cell and day of year, drawn from all 4018 baseline "
        "days 1992-01-01..2002-12-31 (values from 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 were "
        "downloaded and available but contribute to no pool). Quantiles use the Hazen (Hyndman-Fan type 5) "
        "definition as MATLAB quantile does by default; day-60 threshold/climatology set to the mean of days 59 "
        "and 61 before the wrap-around 31-day moving-mean smoothing."
    ),
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print(open('/work/output/report.json').read()[:1500])
