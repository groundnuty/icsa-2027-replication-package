import numpy as np, xarray as xr, json, os, datetime as dt, time
t0=time.time()
os.makedirs('/work/output', exist_ok=True)
base = np.load('/tmp/base.npy'); tgt = np.load('/tmp/tgt.npy')
thr_s = np.load('/tmp/thr_s.npy'); clm_s = np.load('/tmp/clm_s.npy')
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
tt = ds['time'].values.astype('datetime64[D]')
lat = ds['latitude'].values[551:611]; lon = ds['longitude'].values[649:709]
tgt_dates = tt[13665:13757]

CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy366(d): return int(CUM[d.month-1]+d.day)
doys = np.array([doy366(dt.date.fromisoformat(str(x))) for x in tgt_dates])
print('target doys', doys[0], '..', doys[-1], 'unique', np.unique(np.diff(doys)))

land = ~np.isfinite(tgt).all(axis=0); sea = ~land
T64 = tgt.astype(np.float64)
thr_t = thr_s[doys-1]          # (92,60,60) float64
clm_t = clm_s[doys-1]
hot = T64 >= thr_t             # land: thr nan -> False
print('hot days total (sea):', int(hot[:, sea].sum()), 'of', int(sea.sum())*92)

from numpy.lib.stride_tricks import sliding_window_view
def runs_ge(mask, L):
    T, N = mask.shape
    pad = np.zeros((T+L-1, N), bool); pad[L-1:L-1+T] = mask
    starts = sliding_window_view(pad, L, axis=0).all(axis=2)   # (T,N)
    res = starts.copy()
    for k in range(1, L): res[k:] |= starts[:-k]
    return res
def dilate(mask, r):
    out = mask.copy()
    for k in range(1, r+1):
        out[k:] |= mask[:-k]; out[:-k] |= mask[k:]
    return out

hot5 = runs_ge(hot, 5)
joined = dilate(hot5, 2) & dilate(hot, 2)
print('cells with >=1 per-cell MHW day:', int(joined[:, sea].any(axis=0).sum()), 'of', int(sea.sum()))
print('total per-cell MHW days:', int(joined[:, sea].sum()))
# per-cell event listing (compact)
ev_counts = []
for j in range(60):
    for i in range(60):
        if not sea[j,i]: continue
        m = joined[:,j,i]
        if not m.any(): continue
        d = np.diff(np.concatenate(([0], m.view(np.int8), [0])))
        st = np.flatnonzero(d==1); en = np.flatnonzero(d==-1)-1
        ev_counts.append(len(st))
ev_counts = np.array(ev_counts)
print('per-cell MHW event counts: cells with events', ev_counts.size, 'total events', ev_counts.sum(),
      'min/med/max per cell', ev_counts.min(), int(np.median(ev_counts)), ev_counts.max())

active = joined[:, sea].any(axis=1)     # land can't be True, but restrict to sea anyway
d = np.diff(np.concatenate(([0], active.view(np.int8), [0])))
st = np.flatnonzero(d==1); en = np.flatnonzero(d==-1)-1
events = [(str(tgt_dates[a]), str(tgt_dates[b])) for a,b in zip(st,en)]
print('regional events:', len(events))
for a,b in zip(st,en): print('  ', tgt_dates[a], '->', tgt_dates[b], 'len', b-a+1)
print('active days total:', int(active.sum()))
print('active mask by week:', [''.join('1' if x else '.' for x in active[k*7:(k+1)*7]) for k in range(14)])

# ---- write outputs ----
mhw = joined.astype(np.uint8)
assert mhw.dtype == np.uint8 and mhw.shape == (92,60,60) and mhw[:, ~sea].max(initial=0) == 0
out = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw)},
    coords={'time': ('time', tgt_dates.astype('datetime64[ns]')),
            'lat': ('lat', lat), 'lon': ('lon', lon)},
)
out['mhw'].encoding = {'dtype':'uint8', '_FillValue': None}
out['time'].encoding = {'units':'days since 2019-06-01 00:00:00','calendar':'proleptic_gregorian'}
out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
report = {
  "region": {"lat_min": 64.51, "lat_max": 65.71, "lon_min": 21.97, "lon_max": 23.17},
  "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
  "target_analysed": {"start": "2019-06-01", "end": "2019-08-31"},
  "events": [{"onset": a, "end": b} for a,b in events],
  "complete": True,
  "caveats": "Per the method, the +/-5-calendar-day windows around baseline dates extend up to 5 days beyond the 1992-2002 baseline (1991-12-27..1991-12-31 and 2003-01-01..2003-01-05); these extension days were used in the pools. Land cells (SST not finite on every target day) are 0; the NaN mask is identical over the baseline and target periods.",
}
with open('/work/output/report.json','w') as f: json.dump(report, f, indent=2)
print('files written, t=%.1fs' % (time.time()-t0))
print(json.dumps(report, indent=2)[:1200])
