import numpy as np, datetime as dt, json, pickle, fsspec, xarray as xr, warnings, os
warnings.filterwarnings('ignore')

cache = '/tmp/mhw_cache'
cube = np.load(f'{cache}/cube.npy')
with open(f'{cache}/dates.json') as f:
    dates = [dt.date.fromisoformat(s) for s in json.load(f)]
nb = 4028
base = cube[:nb].astype('float64')
tgt = cube[nb:].astype('float64')
dates_t = dates[nb:]
with open(f'{cache}/pools.pkl','rb') as f:
    pools = pickle.load(f)
thresh_s = np.load(f'{cache}/thresh_s.npy')
mhw = np.load(f'{cache}/mhw.npy')
sea = np.load(f'{cache}/sea.npy')

def doy(dd):
    leap = dd.year % 4 == 0 and (dd.year % 100 != 0 or dd.year % 400 == 0)
    tt = dd.timetuple().tm_yday
    return tt + 1 if (not leap and dd.month > 2) else tt

# --- independent end-to-end check: fresh platform read + from-scratch threshold ---
dstr = '20210715'; dd = dt.date(2021,7,15); d = doy(dd)
ti = dates_t.index(dd)
fs = fsspec.filesystem('onedata'); basep = 'icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{basep}/sst_{dstr}.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    fresh = ds['analysed_sst'][0, 130:190, 78:138].values.astype('float64')
print('cube matches fresh platform read for 2021-07-15:', bool(np.array_equal(fresh, tgt[ti], equal_nan=True)))

r, c = 32, 3
print(f'doy({dd}) = {d}')
pool = pools[d]
vals = base[pool, r*1, c] if False else base[pool][:, r, c]
t_raw = np.percentile(vals, 90, method='hazen')
rows = np.array([(d + k - 1) % 366 for k in range(-15, 16)])
t_sm_scratch = thresh_raw_check = base  # placeholder to avoid confusion
# recompute smoothing from scratch using raw percentiles for doys d-15..d+1 (all stored? recompute raw)
raws = {}
for dd2 in range(d-15, d+16):
    dd2m = (dd2 - 1) % 366 + 1
    v = base[pools[dd2m]][:, r, c]
    raws[dd2m] = np.percentile(v, 90, method='hazen')
t_sm = float(np.mean([raws[(d + k - 1) % 366 + 1] for k in range(-15, 16)]))
print('from-scratch smoothed threshold:', round(t_sm, 6), '| stored:', round(float(thresh_s[d, r*60+c]), 6),
      '| diff:', abs(t_sm - float(thresh_s[d, r*60+c])))
print('SST that day (r,c):', round(float(tgt[ti, r, c]), 4), 'K | hot?', bool(tgt[ti, r, c] >= thresh_s[d, r*60+c]),
      '| mhw flag:', int(mhw[ti, r, c]))

# --- active day pattern around event boundaries ---
cnt = mhw.reshape(len(dates_t), -1).sum(axis=1)
for s in ['2021-06-01','2021-06-02','2021-06-03','2021-06-04','2021-06-05','2021-07-27','2021-07-28','2021-07-29','2021-07-30','2021-08-31']:
    i = dates_t.index(dt.date.fromisoformat(s))
    print(s, 'cells in MHW:', int(cnt[i]), '| active:', bool(cnt[i] > 0))
nz = np.where(cnt > 0)[0]
print('first active day:', dates_t[int(nz[0])], '| last active day:', dates_t[int(nz[-1])],
      '| contiguous?', bool((np.diff(nz) == 1).all()))
print('max cells in MHW on a day:', int(cnt.max()), 'on', dates_t[int(np.argmax(cnt))])