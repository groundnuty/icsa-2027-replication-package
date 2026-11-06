import xarray as xr, numpy as np, json
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print('mhw dtype:', ds['mhw'].dtype, '| dims:', ds['mhw'].dims)
print('time dtype:', ds['time'].dtype, 'n:', ds['time'].size)
print('lat first/last:', float(ds.lat[0]), float(ds.lat[-1]))
print('lon first/last:', float(ds.lon[0]), float(ds.lon[-1]))
m = ds['mhw'].values
print('mhw unique:', np.unique(m), 'sum:', int(m.sum()))
# verify mask matches recomputed
mhw = np.load('/work/mhw_mask.npy')
print('matches computed mask:', np.array_equal(m.astype(bool), mhw))
# verify against fresh recomputation from raw arrays
datestrs = np.load('/work/extract_dates.npy')
arr32 = np.load('/work/extract_sst.npy')
dates = [dt.date.fromisoformat(s) for s in datestrs] if (dt:=__import__('datetime')) else None
n_base_win = sum(1 for d in dates if d <= dt.date(2003,1,5))
thr_s3 = np.load('/work/thr_s.npy'); sea = np.load('/work/sea_mask.npy')
sst_t = arr32[n_base_win:].astype(np.float64)
def mdoy(d):
    if d.month<=2: return (d-dt.date(d.year,1,1)).days+1
    leap=(d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    return (d-dt.date(d.year,1,1)).days+1+(0 if leap else 1)
doys = np.array([mdoy(d) for d in dates[n_base_win:]])
hot = (sst_t >= thr_s3[doys-1]) & sea[None,:,:]
idx_ok = True
# quick re-run detection to double-check
import numpy as _np
def detect(hot, sea):
    m = _np.zeros_like(hot)
    for a in range(hot.shape[1]):
        for b in range(hot.shape[2]):
            if not sea[a,b]: continue
            idx = _np.flatnonzero(hot[:,a,b])
            if idx.size==0: continue
            br = _np.where(_np.diff(idx)>1)[0]
            st = _np.concatenate(([0],br+1)); en = _np.concatenate((br,[idx.size-1]))
            runs = [[idx[s],idx[e]] for s,e in zip(st,en) if idx[e]-idx[s]+1>=5]
            if not runs: continue
            j=[runs[0]]
            for r in runs[1:]:
                if r[0]-j[-1][1]-1<=2: j[-1][1]=r[1]
                else: j.append(r)
            for s,e in j: m[s:e+1,a,b]=True
    return m.astype(bool)
m2 = detect(hot, sea)
print('fresh recomputation matches:', np.array_equal(m2, m.astype(bool)))
ds.close()
# JSON schema check
r = json.load(open('/work/output/report.json'))
print('report keys:', sorted(r.keys()))
assert set(r.keys()) == {'region','baseline_analysed','target_analysed','events','complete','caveats'}
print('schema OK; complete:', r['complete'])
