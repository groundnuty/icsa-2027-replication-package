import numpy as np, pandas as pd, xarray as xr, json, os

os.makedirs('output', exist_ok=True)
z = np.load('/work/final.npz')
per_cell, sea = z['per_cell'], z['sea']
tgt_dates = pd.read_pickle('/work/tgt_dates.pkl')

def find_runs(f_, minlen):
    runs=[]; n=len(f_); i=0
    while i < n:
        if f_[i]:
            j=i
            while j+1<n and f_[j+1]: j+=1
            if j-i+1>=minlen: runs.append([i,j])
            i=j+1
        else: i+=1
    return runs
def join_runs(runs, maxgap):
    if not runs: return []
    m=[runs[0][:]]
    for s,e in runs[1:]:
        gap=s-m[-1][1]-1
        if 1<=gap<=maxgap: m[-1][1]=e
        else: m.append([s,e])
    return m

active = per_cell.any(axis=(1,2))
regional = join_runs(find_runs(active,1),0)
print("regional events:", [[str(tgt_dates.iloc[s].date()), str(tgt_dates.iloc[e].date())] for s,e in regional])

report = {
    "region": {"lat_min": 62.25, "lat_max": 63.45, "lon_min": 18.73, "lon_max": 19.93},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2012-06-01", "end": "2012-08-31"},
    "events": [{"onset": str(tgt_dates.iloc[s].date()), "end": str(tgt_dates.iloc[e].date())} for s,e in regional],
    "complete": True,
    "caveats": ("Region bounds snap to the dataset's ~0.02-degree grid: analysed cells span lat 62.26-63.44N, lon 18.74-19.92E (60x60 cells; 3308 sea cells = cells with finite SST on all 92 target days). "
                "Threshold/climatology pools cover the full prescribed 1992-2002 baseline plus the +/-5-day edge windows, so SST from 1991-12-27 to 2003-01-05 was actually used (121 values per pool, all finite on sea cells). "
                "Hot-day comparison uses kelvin SST as stored; percentile is Hazen (Hyndman-Fan type 5) in float64; smoothing is an unweighted centred 31-day mean wrapping modulo 366 days. "
                "One regional event found: 2012-08-15 to 2012-08-19; the same 26 cells are in per-cell MHW on each of its 5 days, and no other cell reached 5 consecutive hot days in the target period.")
}
with open('output/mhw_report.json','w') as fh:
    json.dump(report, fh, indent=2)
print("written:", sorted(os.listdir('output')))
print(json.dumps(json.load(open('output/mhw_report.json')), indent=1))
