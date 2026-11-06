import numpy as np, datetime as dt, json, os, warnings
warnings.filterwarnings('ignore')

# ---------------- inputs ----------------
Barr = np.load('/work/baseline_sst.npy')      # (4028,60,60) float64, 1991-12-27..2003-01-05
T    = np.load('/work/target_sst.npy')        # (92,60,60) float64, 2005-06-01..2005-08-31
tstr = np.load('/work/target_datestr.npy')
lat_vals = np.load('/work/lat_vals.npy')      # float32 dataset lat values of region cells (ascending)
lon_vals = np.load('/work/lon_vals.npy') if os.path.exists('/work/lon_vals.npy') else None
if lon_vals is None:
    import xarray as xr
    with xr.open_dataset('/work/tmp/sample.nc', engine='h5netcdf') as ds:
        lat_idx = np.load('/work/lat_idx.npy'); lon_idx = np.load('/work/lon_idx.npy')
        lat_vals = ds['latitude'].values[lat_idx].astype(np.float32)
        lon_vals = ds['longitude'].values[lon_idx].astype(np.float32)
        np.save('/work/lon_vals.npy', lon_vals); np.save('/work/lat_vals.npy', lat_vals)
else:
    lat_idx = np.load('/work/lat_idx.npy'); lon_idx = np.load('/work/lon_idx.npy')
    with xr.open_dataset('/work/tmp/sample.nc', engine='h5netcdf') as ds:
        assert np.array_equal(ds['latitude'].values[lat_idx].astype(np.float32), lat_vals)
        assert np.array_equal(ds['longitude'].values[lon_idx].astype(np.float32), lon_vals)

CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def mdoy(y,m,d): return CUM[m-1]+d

ext_start = dt.date(1991,12,27)
cdates = [ext_start + dt.timedelta(i) for i in range(Barr.shape[0])]
md = np.array([mdoy(c.year,c.month,c.day) for c in cdates])
ib = np.array([dt.date(1992,1,1) <= c <= dt.date(2002,12,31) for c in cdates])

# ---------------- thresholds & climatology ----------------
thr  = np.full((366,)+Barr.shape[1:], np.nan)
clim = np.full_like(thr, np.nan)
for d in range(1,367):
    if d==60: continue
    ci = np.flatnonzero(ib & (md==d))
    idx = np.unique(np.concatenate([np.arange(max(i-5,0), min(i+5,Barr.shape[0]-1)+1) for i in ci]))
    pool = Barr[idx]
    thr[d-1]  = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clim[d-1] = np.nanmean(pool, axis=0)
thr[59]  = 0.5*(thr[58]+thr[60])     # day 60 (29 Feb) = mean of days 59 and 61
clim[59] = 0.5*(clim[58]+clim[60])

def smooth31(a):   # unweighted centred 31-day moving mean, wrap mod 366
    p = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(p, axis=0)
    s = c[30:].copy(); s[1:] = c[31:] - c[:-31]
    return s/31.0
thr_s, clim_s = smooth31(thr), smooth31(clim)

# ---------------- sea cells & hot days ----------------
sea = np.isfinite(T).all(axis=0)
tdoy = np.array([mdoy(int(s[:4]),int(s[4:6]),int(s[6:])) for s in tstr])
hot = T >= thr_s[tdoy-1]          # (92,60,60) bool, float64 compare

# ---------------- per-cell MHWs ----------------
def runs_of_true(h):
    idx = np.flatnonzero(h)
    if idx.size==0: return []
    br = np.flatnonzero(np.diff(idx)>1)
    return list(zip(np.concatenate([[idx[0]],idx[br+1]]).tolist(),
                    np.concatenate([idx[br],[idx[-1]]]).tolist()))
def cell_mhw_intervals(h):
    runs = [(s,e) for s,e in runs_of_true(h) if e-s+1>=5]
    if not runs: return []
    merged=[list(runs[0])]
    for s,e in runs[1:]:
        if s-merged[-1][1]-1 <= 2: merged[-1][1]=e
        else: merged.append([s,e])
    return [(s,e) for s,e in merged]

mhw = np.zeros(hot.shape, np.uint8)
n_ev=0
for r in range(mhw.shape[1]):
    for c in range(mhw.shape[2]):
        if not sea[r,c]: continue
        for s,e in cell_mhw_intervals(hot[:,r,c]):
            mhw[s:e+1,r,c]=1; n_ev+=1

# ---------------- regional events ----------------
active = mhw.any(axis=(1,2))
ev = runs_of_true(active)
dates = [dt.date(int(s[:4]),int(s[4:6]),int(s[6:])) for s in tstr]
events_json = [{'onset': dates[s].isoformat(), 'end': dates[e].isoformat()} for s,e in ev]

print('sea cells:', int(sea.sum()), '| per-cell MHWs:', n_ev)
print('regional events:', events_json)

# ---------------- write outputs ----------------
import xarray as xr
os.makedirs('/work/output', exist_ok=True)
ds_out = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw.astype(np.uint8))},
    coords={'time': np.array(dates, dtype='datetime64[ns]'),
            'lat': lat_vals.astype(np.float32),
            'lon': lon_vals.astype(np.float32)},
    attrs={'title': 'Marine heatwave mask (per-cell MHW), Baltic Sea region',
           'region': 'lat 55.67-56.87 N, lon 16.45-17.65 E',
           'baseline': '1992-01-01 to 2002-12-31 (+-5-day windows, day 60 filled from d59/d61)',
           'threshold': '90th percentile (hazen/type 5) of +-5-day pools, 31-day wrapped moving mean',
           'target_period': '2005-06-01 to 2005-08-31',
           'mhw_definition': 'hot (SST >= threshold) runs >= 5 days, gaps <= 2 days joined',
           'source': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP_OBSERVATIONS_010_016)'})
ds_out['lat'].attrs = {'units':'degrees_north','standard_name':'latitude'}
ds_out['lon'].attrs = {'units':'degrees_east','standard_name':'longitude'}
ds_out['mhw'].attrs = {'long_name':'per-cell marine heatwave mask','flag_values':np.array([0,1],np.uint8),
                       'flag_meanings':'not_in_mhw in_mhw'}
enc = {'mhw': {'dtype':'uint8','_FillValue':None},
       'lat': {'_FillValue':None}, 'lon': {'_FillValue':None}}
ds_out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf', encoding=enc)

report = {'region': {'lat_min':55.67,'lat_max':56.87,'lon_min':16.45,'lon_max':17.65},
          'baseline_analysed': {'start':'1992-01-01','end':'2002-12-31'},
          'target_analysed': {'start':'2005-06-01','end':'2005-08-31'},
          'events': events_json,
          'complete': True,
          'caveats': ('Sea cells = 3310 of 3600 region grid cells with finite SST on all 92 target days; '
                      'land cells are 0. Threshold/climatology pools per the specified method also include '
                      'the 10 edge-extension days 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05; all 4028 '
                      'window days were present (no missing files). SST is stored as float32 kelvin; all '
                      'computations in float64. Per-cell MHW detection uses only 2005-06-01..2005-08-31, so a '
                      'run straddling the period start would be measured from 2005-06-01 (earliest detected '
                      'onset here was 2005-07-02, so no such truncation occurred).')}
with open('/work/output/report.json','w') as f:
    json.dump(report, f, indent=2)
print('files written')
