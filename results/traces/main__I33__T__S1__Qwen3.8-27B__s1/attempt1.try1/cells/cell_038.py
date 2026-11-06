
import json, pickle, os
with open('/work/work/events.pkl','rb') as f: events = pickle.load(f)
print("events:", events)

report = {
    "region": {"lat_min": 59.05, "lat_max": 60.25, "lon_min": 21.25, "lon_max": 22.45},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2014-06-01", "end": "2014-08-31"},
    "events": [{"onset": e[0], "end": e[1]} for e in events],
    "complete": True,
    "caveats": ("Region comprises the 60x60 dataset grid points (0.02 deg grid) inside the inclusive bounds "
                "(lat 59.06-60.24, lon 21.26-22.44); 3290 of 3600 cells had finite SST on all 92 target days and were treated as sea cells. "
                "Thresholds use the 1992-2002 baseline with 5-day day-of-year windows extended to 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05; "
                "day-of-year 60 has no own pool and was set to the mean of days 59 and 61 before 31-day centred circular smoothing; "
                "90th percentile computed with hazen (Hyndman-Fan type 5, MATLAB default) quantile in float64.")
}
with open('/work/output/report.json','w') as f:
    json.dump(report, f, indent=2)
print(open('/work/output/report.json').read())
print("files:", os.listdir('/work/output'))
