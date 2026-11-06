import numpy as np, xarray as xr, json, os
os.makedirs('output', exist_ok=True)
z = np.load('work/sst.npz')
ST, tt = z['ST'], z['tt']
z2 = np.load('work/thr.npz')
sea, thr_s = z2['sea'], z2['thr_s']
lat, lon = z['lat'], z['lon']   # float32, dataset values
n_cells = 3600
STf = ST.reshape(92, n_cells)
from datetime import date, timedelta
doy_md = {}
d = date(2004,1,1)
for k in range(366):
    doy_md[k+1] = (d.month, d.day); d += timedelta(days=1)
md2d = {v:k for k,v in doy_md.items()}
t_doys = np.array([md2d[(date.fromisoformat(ts.astype('datetime64[D]').astype(str)).month,
                         date.fromisoformat(ts.astype('datetime64[D]').astype(str)).day)] for ts in tt])

hot = STf >= thr_s[:, t_doys-1].T

def mhw_mask(hot_row):
    d = np.diff(np.concatenate(([0], hot_row.view(np.int8), [0])))
    starts = np.where(d == 1)[0]; ends = np.where(d == -1)[0] - 1
    keep = (ends - starts + 1) >= 5
    starts, ends = starts[keep], ends[keep]
    mask = np.zeros(len(hot_row), dtype=bool)
    if len(starts):
        s0, e0 = starts[0], ends[0]
        for s, e in zip(starts[1:], ends[1:]):
            if s - e0 - 1 <= 2: e0 = e
            else:
                mask[s0:e0+1] = True; s0, e0 = s, e
        mask[s0:e0+1] = True
    return mask

mask_cells = np.zeros((n_cells, 92), dtype=bool)
for c in np.where(sea)[0]:
    mask_cells[c] = mhw_mask(hot[:, c])
mhw = mask_cells.T.reshape(92, 60, 60).astype(np.uint8)
print("mhw sum:", int(mhw.sum()), "shape:", mhw.shape)

active = mask_cells.any(axis=0)
ddv = np.diff(np.concatenate(([0], active.view(np.int8), [0])))
starts = np.where(ddv == 1)[0]; ends = np.where(ddv == -1)[0] - 1
events = [{"onset": str(tt[s].astype('datetime64[D]')), "end": str(tt[e].astype('datetime64[D]'))}
          for s, e in zip(starts, ends)]
print("events:", events)

out = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mhw)},
    coords={'time': tt.astype('datetime64[ns]'),
            'lat': lat.astype(np.float32),
            'lon': lon.astype(np.float32)}
)
out['mhw'].attrs = {'long_name': 'marine heatwave mask (1 = inside per-cell MHW, 0 = not)',
                    'flag_values': 0, 'flag_meanings': 'no mhw'}
out.attrs = {
    'title': 'Baltic Sea regional MHW mask, 2004-06-01 to 2004-08-31',
    'source': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (sst_s2.nc, analysed_sst)',
    'method': 'threshold = smoothed(31d) 90th pct (hazen) of +/-5-day pool from 1992-2002 baseline (incl. 1991-12-27..31, 2003-01-01..05); MHW = >=5 consecutive hot days, gaps <=2 days joined; sea cells finite on all target days',
    'region': 'lat 54.17-55.37 N, lon 13.25-14.45 E (grid cells 54.18-55.36, 13.26-14.44)',
}
out.to_netcdf('output/mhw_mask.nc')

report = {
    "region": {"lat_min": 54.17, "lat_max": 55.37, "lon_min": 13.25, "lon_max": 14.45},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("No per-cell MHWs (>=5 consecutive hot days) were found, so no regional events. "
                "The summer 2004 SST in this region ran below the smoothed 90th-percentile threshold derived from the "
                "1992-2002 baseline on nearly all days (region-mean offset about -0.38 K vs baseline climatology, -2.6 K on 2004-07-15; "
                "largest single-day positive margin +1.02 K on 2004-08-01). 117 hot cell-days occurred, longest run in any cell 2 days. "
                "3303 of 3600 region cells are sea cells (finite on all 92 target days); all sea cells have fully defined thresholds. "
                "Land cells are set to 0 in the mask.")
}
with open('output/report.json', 'w') as fh:
    json.dump(report, fh, indent=2)
print("files written")
print(open('output/report.json').read())
