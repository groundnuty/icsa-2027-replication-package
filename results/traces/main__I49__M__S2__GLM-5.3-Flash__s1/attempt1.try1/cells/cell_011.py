import numpy as np, xarray as xr, json, datetime as dt
# fresh read-back of outputs
m = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(m)
A = m['mhw'].values
print('dtype', m['mhw'].dtype, 'dims', m['mhw'].dims, 'shape', A.shape)
mt = m['time'].values.astype('datetime64[D]')
exp_dates = np.array([np.datetime64('2019-06-01')+np.timedelta64(k,'D') for k in range(92)])
print('time OK:', np.array_equal(mt, exp_dates), mt[0], mt[-1])
tgt = np.load('/tmp/tgt.npy'); thr_s = np.load('/tmp/thr_s.npy')
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
doys = np.array([int(CUM[dt.date.fromisoformat(str(x)).month-1]+dt.date.fromisoformat(str(x)).day) for x in exp_dates])
land = ~np.isfinite(tgt).all(axis=0); sea = ~land
hot = tgt.astype(np.float64) >= thr_s[doys-1]
# recompute per-cell mask from scratch (brute) and compare to file
ref = np.zeros_like(hot)
for j in range(60):
    for i in range(60):
        if not sea[j,i]: continue
        h = hot[:,j,i]; runs=[]; k=0
        while k<92:
            if h[k]:
                l=k
                while l+1<92 and h[l+1]: l+=1
                if l-k+1>=5: runs.append((k,l))
                k=l+1
            else: k+=1
        if runs:
            merged=[list(runs[0])]
            for a,b in runs[1:]:
                if a-merged[-1][1]-1<=2: merged[-1][1]=b
                else: merged.append([a,b])
            for a,b in merged: ref[a:b+1,j,i]=True
print('file mask == independent brute-force recompute:', np.array_equal(A.astype(bool), ref))
print('land all zero:', bool(A[:,~sea].max()==0), '| unique values:', np.unique(A), '| sum:', int(A.sum()))
act = ref[:,sea].any(axis=1)
d = np.diff(np.concatenate(([0], act.view(np.int8), [0])))
st = np.flatnonzero(d==1); en = np.flatnonzero(d==-1)-1
evs = [(str(exp_dates[a]), str(exp_dates[b])) for a,b in zip(st,en)]
print('events from file-derived mask:', evs)
# mask subset of hot ∪ 2-day halo (gap days are non-hot but included)
halo = hot.copy()
for s in (1,2):
    halo[s:] |= hot[:-s]; halo[:-s] |= hot[s:]
print('all mask days are hot or within 2 days of hot (gap logic consistent):', bool((A.astype(bool) <= halo).all()))

rep = json.load(open('/work/output/report.json'))
print('\nreport.json:')
print(json.dumps(rep, indent=2))
assert set(rep) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert rep["events"] == [{"onset":a,"end":b} for a,b in evs]
assert rep["complete"] is True and rep["baseline_analysed"] == {"start":"1992-01-01","end":"2002-12-31"}
assert rep["target_analysed"] == {"start":"2019-06-01","end":"2019-08-31"}
assert rep["region"] == {"lat_min":64.51,"lat_max":65.71,"lon_min":21.97,"lon_max":23.17}
print('report schema + content checks: OK')
# coordinate values match dataset
with xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf') as dsrc:
    lat = dsrc['latitude'].values[551:611]; lon = dsrc['longitude'].values[649:709]
    dtm = dsrc['time'].values[13665:13757]
print('coords match dataset:', np.array_equal(m['lat'].values, lat), np.array_equal(m['lon'].values, lon),
      np.array_equal(m['time'].values.astype('datetime64[D]'), dtm.astype('datetime64[D]')))
