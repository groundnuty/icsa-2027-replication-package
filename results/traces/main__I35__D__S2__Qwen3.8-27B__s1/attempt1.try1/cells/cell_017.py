import json, os, numpy as np, pickle
d1 = pickle.load(open('/work/step1.pkl','rb'))
d3 = pickle.load(open('/work/step3.pkl','rb'))
t_tgt = d1['t_tgt']; ev = d3['events']
report = {
    'region': {'lat_min': 59.93, 'lat_max': 61.13, 'lon_min': 18.69, 'lon_max': 19.89},
    'baseline_analysed': {'start': '1991-12-27', 'end': '2003-01-05'},
    'target_analysed': {'start': '2009-06-01', 'end': '2009-08-31'},
    'events': [{'onset': str(t_tgt[s])[:10], 'end': str(t_tgt[e])[:10]} for s, e in ev],
    'complete': True,
    'caveats': ('Region = 60x60 grid cells (lat 59.94-61.12N, lon 18.70-19.88E on the 0.02-deg grid) inside the inclusive bounds. '
                'SST in kelvin as stored. 1956 of 3600 cells were sea cells (finite SST on all 92 target days); land/missing cells are 0. '
                'Thresholds = hazen (Hyndman-Fan type 5) 90th percentile of the per-day-of-year pool of baseline days 1992-2002 with +/-5 '
                'calendar-day windows (pool dates 1991-12-27 to 2003-01-05, 121 days each; Feb 29 values in the neighbour windows; day 60 = '
                'mean of days 59 and 61), then 31-day centred circular moving mean. Per-cell MHW = >=5 consecutive days with SST >= threshold, '
                'runs joined across 1-2 non-hot gaps; regional event = maximal run of days with >=1 sea cell in an MHW. '
                'One regional event covers the entire target period.')
}
p = os.path.join(os.getcwd(), 'output', 'report.json')
with open(p, 'w') as f:
    json.dump(report, f, indent=2)
print(open(p).read())
# final validation of both files
import xarray as xr, re
chk = xr.open_dataset(os.path.join(os.getcwd(), 'output', 'mhw_mask.nc'), engine='h5netcdf')
assert str(chk['mhw'].dtype) == 'uint8'
assert list(chk['mhw'].dims) == ['time', 'lat', 'lon']
assert chk.sizes['time'] == 92 and chk.sizes['lat'] == 60 and chk.sizes['lon'] == 60
assert np.array_equal(chk['time'].values, t_tgt)
rep = json.load(open(p))
assert list(rep.keys()) == ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
assert rep['events'] == [{'onset': '2009-06-01', 'end': '2009-08-31'}]
for k in ('onset', 'end'):
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', rep['events'][0][k])
print('ALL FINAL CHECKS PASSED')
