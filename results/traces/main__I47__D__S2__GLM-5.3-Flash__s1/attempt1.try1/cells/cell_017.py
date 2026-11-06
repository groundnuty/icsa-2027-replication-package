import numpy as np, xarray as xr, json, os, datetime as dt

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
thr_s = np.load('/work/thr_s.npy')
L0, L1, O0, O1 = 545, 604, 721, 780

sst_t = ds['analysed_sst'].isel(time=slice(13665, 13757), latitude=slice(L0, L1+1), longitude=slice(O0, O1+1)).values.astype(np.float64)
tdates = np.arange('2019-06-01', '2019-09-01', dtype='datetime64[D]')
tdoy = np.array([dt.date(2019, int(str(t)[5:7]), int(str(t)[8:10])).timetuple().tm_yday for t in tdates])
print('target doy range:', tdoy.min(), '..', tdoy.max())

sea = np.isfinite(sst_t).all(axis=0)
print('sea cells:', int(sea.sum()), '/', sea.size)

with np.errstate(invalid='ignore'):
    hot = sst_t >= thr_s[tdoy-1]
print('hot cell-days:', int(hot.sum()), 'of %d (%.1f%%)' % (hot.size, 100*hot.sum()/hot.size))

T, NY, NX = 92, 60, 60
hotf = hot.reshape(T, -1).astype(np.int8)
padded = np.concatenate([np.zeros((1, hotf.shape[1]), np.int8), hotf, np.zeros((1, hotf.shape[1]), np.int8)])
d = np.diff(padded, axis=0)
sr, sc = np.nonzero(d == 1); er, ec = np.nonzero(d == -1)
o1 = np.lexsort((sr, sc)); sr2, sc2 = sr[o1], sc[o1]
o2 = np.lexsort((er, ec)); er2, ec2 = er[o2], ec[o2]
assert (sc2 == ec2).all()
L = er2 - sr2
cand = L >= 5
cs, ce, cc = sr2[cand], er2[cand], sc2[cand]
print('hot runs:', len(sr), '| candidates (>=5d):', len(cs))

merged = []
i, n = 0, len(cs)
while i < n:
    j, s, e, c = i, cs[i], ce[i], cc[i]
    while j+1 < n and cc[j+1] == c and cs[j+1] - e <= 2:
        j += 1; e = ce[j]
    merged.append((int(c), int(s), int(e))); i = j+1
print('per-cell MHWs after joining:', len(merged))

mhw = np.zeros((T, NY*NX), dtype=np.uint8)
for c, s, e in merged: mhw[s:e, c] = 1
mhw = mhw.reshape(T, NY, NX)

def per_cell_mask(hc):
    T = len(hc); runs = []; t = 0
    while t < T:
        if hc[t]:
            u = t
            while u < T and hc[u]: u += 1
            runs.append((t, u)); t = u
        else: t += 1
    out = []
    for r in [r for r in runs if r[1]-r[0] >= 5]:
        if out and r[0] - out[-1][1] <= 2: out[-1] = (out[-1][0], r[1])
        else: out.append(r)
    m = np.zeros(T, np.uint8)
    for s, e in out: m[s:e] = 1
    return m
mhw2 = np.stack([per_cell_mask(hotf[:, c]) for c in range(hotf.shape[1])], axis=1).reshape(T, NY, NX)
print('vectorized == brute force:', bool((mhw == mhw2).all()))
print('mask days with any cell in MHW:', int((mhw.reshape(T,-1).any(axis=1)).sum()), 'of', T)
print('max cells in MHW on one day:', int(mhw.reshape(T,-1).sum(axis=1).max()))

active = mhw.reshape(T, -1).any(axis=1)
events = []
t = 0
while t < T:
    if active[t]:
        u = t
        while u < T and active[u]: u += 1
        events.append((int(t), int(u-1))); t = u
    else: t += 1
print('regional events:', len(events))
for s, e in events:
    cells = mhw[s:e+1].reshape(e+1-s, -1).sum(axis=1)
    print('  %s .. %s (%d days, cells/day %d..%d)' % (tdates[s], tdates[e], e-s+1, cells.min(), cells.max()))
np.save('/work/mhw.npy', mhw); np.save('/work/active.npy', active)
