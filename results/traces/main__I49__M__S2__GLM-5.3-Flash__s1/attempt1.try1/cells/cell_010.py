import numpy as np, xarray as xr, json, os, datetime as dt, time
t0=time.time()
os.makedirs('/work/output', exist_ok=True)
tgt = np.load('/tmp/tgt.npy'); thr_s = np.load('/tmp/thr_s.npy')
p='/data/icsa20261101T090944Z_placeholder'
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
tt = ds['time'].values.astype('datetime64[D]')
lat = ds['latitude'].values[551:611]; lon = ds['longitude'].values[649:709]
tgt_dates = tt[13665:13757]
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
doys = np.array([int(CUM[dt.date.fromisoformat(str(x)).month-1]+dt.date.fromisoformat(str(x)).day) for x in tgt_dates])
land = ~np.isfinite(tgt).all(axis=0); sea = ~land

hot = (tgt.astype(np.float64) >= thr_s[doys-1]).reshape(92,-1)

def runs_ge5(m):
    T,N = m.shape
    starts = m.copy(); starts[1:] &= ~m[:-1]
    rid = np.cumsum(starts, axis=0)
    uid = rid + np.arange(N)[None,:]*(T+1)
    lens = np.bincount(uid[m].ravel(), minlength=N*(T+1))
    return m & (lens[uid] >= 5)

def join_runs(q, h):
    T,N = h.shape; out = np.zeros_like(h)
    for n in range(N):
        mm = q[:,n]
        if not mm.any(): continue
        d = np.diff(np.concatenate(([0], mm.view(np.int8), [0])))
        st = np.flatnonzero(d==1); en = np.flatnonzero(d==-1)-1
        merged = [[int(a),int(b)] for a,b in zip(st,en)]
        m2 = [merged[0]]
        for a,b in merged[1:]:
            if a - m2[-1][1] - 1 <= 2: m2[-1][1] = b
            else: m2.append([a,b])
        for a,b in m2: out[a:b+1, n] = True
    return out

q = runs_ge5(hot)
joined = join_runs(q, hot)
print('qualifying runs>=5 days:', int(q[:, sea.ravel()].sum()))
print('per-cell MHW days after join:', int(joined[:, sea.ravel()].sum()))
print('cells with >=1 MHW day:', int(joined[:, sea.ravel()].any(axis=0).sum()), 'of', int(sea.sum()))
ev_counts=[]
for n in range(3600):
    if not sea.ravel()[n]: continue
    mm = joined[:,n]
    if not mm.any(): continue
    d = np.diff(np.concatenate(([0], mm.view(np.int8), [0])))
    ev_counts.append(int((d==1).sum()))
ev_counts=np.array(ev_counts)
print('per-cell events: cells', ev_counts.size, 'total', ev_counts.sum(), 'max per cell', ev_counts.max())

active = joined[:, sea.ravel()].any(axis=1)
d = np.diff(np.concatenate(([0], active.view(np.int8), [0])))
st = np.flatnonzero(d==1); en = np.flatnonzero(d==-1)-1
events = [(str(tgt_dates[a]), str(tgt_dates[b])) for a,b in zip(st,en)]
print('regional events:', len(events))
for a,b in zip(st,en): print('  ', tgt_dates[a], '->', tgt_dates[b], 'len', b-a+1)
print('active day mask (rows of 14):')
for k in range(0,92,14): print('  ', ''.join('1' if x else '.' for x in active[k:k+14]))

# per-cell brute-force cross-check of final mask
ref = np.zeros_like(hot)
for n in range(3600):
    if not sea.ravel()[n]: continue
    h = hot[:,n]; i = 0
    runs=[]
    while i < 92:
        if h[i]:
            j=i
            while j+1<92 and h[j+1]: j+=1
            if j-i+1>=5: runs.append((i,j))
            i=j+1
        else: i+=1
    if runs:
        merged=[list(runs[0])]
        for a,b in runs[1:]:
            if a-merged[-1][1]-1<=2: merged[-1][1]=b
            else: merged.append([a,b])
        for a,b in merged: ref[a:b+1,n]=True
assert np.array_equal(joined, ref), 'vectorized vs brute mismatch'
print('vectorized == brute-force per-cell reference: OK')
# regional brute check
ref_active = ref[:, sea.ravel()].any(axis=1)
assert np.array_equal(active, ref_active)
print('regional active days:', int(active.sum()))

mhw = joined.reshape(92,60,60).astype(np.uint8)
assert mhw.dtype==np.uint8 and mhw.shape==(92,60,60) and mhw[:,~sea].max(initial=0)==0
out = xr.Dataset({'mhw': (('time','lat','lon'), mhw)},
                 coords={'time': ('time', tgt_dates.astype('datetime64[ns]')),
                         'lat': ('lat', lat), 'lon': ('lon', lon)})
out['mhw'].encoding = {'dtype':'uint8','_FillValue': None}
out['time'].encoding = {'units':'days since 2019-06-01 00:00:00','calendar':'proleptic_gregorian'}
out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
report = {
  "region": {"lat_min": 64.51, "lat_max": 65.71, "lon_min": 21.97, "lon_max": 23.17},
  "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
  "target_analysed": {"start": "2019-06-01", "end": "2019-08-31"},
  "events": [{"onset": a, "end": b} for a,b in events],
  "complete": True,
  "caveats": "Per the method, the +/-5-calendar-day windows around baseline dates extend up to 5 days beyond the 1992-2002 baseline (1991-12-27..1991-12-31 and 2003-01-01..2003-01-05); these extension days were included in the pools. Land cells (SST not finite on every target day) are 0; the NaN mask is identical over the baseline and target periods.",
}
with open('/work/output/report.json','w') as f: json.dump(report, f, indent=2)
print('files rewritten, t=%.1fs' % (time.time()-t0))
