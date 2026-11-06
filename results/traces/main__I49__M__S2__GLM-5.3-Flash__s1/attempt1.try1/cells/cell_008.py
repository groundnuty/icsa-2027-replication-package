import numpy as np, xarray as xr, json, datetime as dt, os
# ---- recompute independently (brute force per cell) for cross-check ----
tgt = np.load('/tmp/tgt.npy'); thr_s = np.load('/tmp/thr_s.npy')
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
tgt_dates = np.array([np.datetime64('2019-06-01') + np.timedelta64(k,'D') for k in range(92)])
doys = np.array([int(CUM[dt.date(2019,6,1).__class__.fromisoformat(str(x)).month-1] + dt.date.fromisoformat(str(x)).day) for x in tgt_dates])
land = ~np.isfinite(tgt).all(axis=0); sea = ~land
hot = tgt.astype(np.float64) >= thr_s[doys-1]

def brute_cell(h):  # h: (92,) bool
    # hot runs >=5
    runs = []
    i = 0
    while i < 92:
        if h[i]:
            j = i
            while j+1 < 92 and h[j+1]: j += 1
            if j-i+1 >= 5: runs.append((i,j))
            i = j+1
        else: i += 1
    # join runs separated by 1 or 2 non-hot days
    if not runs: return np.zeros(92, bool)
    joined = [list(runs[0])]
    for (a,b) in runs[1:]:
        gap = a - joined[-1][1] - 1
        if 1 <= gap <= 2: joined[-1][1] = b
        else: joined.append([a,b])
    out = np.zeros(92, bool)
    for a,b in joined: out[a:b+1] = True
    return out

ref = np.zeros_like(hot)
for j in range(60):
    for i in range(60):
        if not sea[j,i]: continue
        ref[:,j,i] = brute_cell(hot[:,j,i])
ref_active = ref[:, sea].any(axis=1)
d = np.diff(np.concatenate(([0], ref_active.view(np.int8), [0])))
st = np.flatnonzero(d==1); en = np.flatnonzero(d==-1)-1
ref_events = [(str(tgt_dates[a]), str(tgt_dates[b])) for a,b in zip(st,en)]
print('brute-force events:', ref_events)

# ---- validate written files ----
m = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(m)
mv = m['mhw']
print('mhw dtype', mv.dtype, 'encoding', {k:v for k,v in mv.encoding.items()})
mt = m['time'].values.astype('datetime64[D]')
print('time first/last', mt[0], mt[-1], 'n', mt.size, 'matches target dates:', np.array_equal(mt, tgt_dates))
print('lat match:', np.array_equal(m['lat'].values, ds_lat := None or np.load('/tmp/tgt.npy').shape and None) )
with xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf') as dsrc:
    lat = dsrc['latitude'].values[551:611]; lon = dsrc['longitude'].values[649:709]
    dtime = dsrc['time'].values[13665:13757].astype('datetime64[D]')
print('lat equal dataset slice:', np.array_equal(m['lat'].values, lat), 'lon equal:', np.array_equal(m['lon'].values, lon))
print('time equal dataset slice:', np.array_equal(mt, dtime))
A = mv.values
print('mask agrees with brute force:', np.array_equal(A.astype(bool), ref))
print('land cells all zero:', bool(A[:, ~sea].max()==0), 'values set:', np.unique(A))
print('mhw days (uint8 sum):', int(A.sum()), '== per-cell days', int(ref.sum()))
rep = json.load(open('/work/output/report.json'))
print('report keys:', sorted(rep.keys()))
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
print('report events == brute force:', rep['events'] == [{"onset":a,"end":b} for a,b in ref_events])
# raw-data spot check: mean SST over sea cells per event day vs neighbours
for day in ['2019-06-06','2019-06-07','2019-06-28','2019-06-29','2019-07-20','2019-07-21','2019-07-31','2019-08-01','2019-08-27','2019-08-28']:
    k = int((np.datetime64(day)-np.datetime64('2019-06-01'))/np.timedelta64(1,'D'))
    print(day, 'region-mean SST %.3f K, active-cells %d' % (tgt[k][sea].mean(), int(A[k].sum())))
print('files:', os.listdir('/work/output'), os.path.getsize('/work/output/mhw_mask.nc'), os.path.getsize('/work/output/report.json'))
