import numpy as np, pandas as pd

z = np.load('/work/interim.npz'); tc = np.load('/work/thr_clim.npz'); m = np.load('/work/mhw.npz')
sst_t, sea = z['sst_t'], z['sea']
thr_s = tc['thr_s']
mask_ref = m['mask']           # (92,60,60) uint8
NC = 3600
nt = 92
i0 = int(z['t_i0'])
ds_t = pd.date_range('2014-06-01', periods=92, freq='D')
assert all(int(a.date().toordinal())==int(b.date().toordinal()) for a,b in zip(pd.to_datetime(np.load('/work/interim.npz') and __import__('xarray').open_dataset('/work/sst_s2.nc', engine='h5netcdf').time.values[int(z['t_i0']):int(z['t_i1'])]), ds_t))

def md_to_doy2(d):  # independent doy: use pandas dayofyear on a leap-year reference
    return None

# independent doy via ordinal difference in a leap year
leap = pd.Timestamp('2016-01-01')
doys_alt = np.array([ (d - leap).days % 366 + 1 if (d - leap).days >= 0 else None for d in ds_t])
# simpler explicit: for date in Jun-Aug 2014, doy = 153 + (d - Jun1).days
doys_alt = 153 + (ds_t - ds_t[0]).days
# sanity against earlier mapping
def md_to_doy(mo, dd):
    if (mo, dd) == (2, 29): return 60
    days = [31,28,31,30,31,30,31,31,30,31,30,31]
    cum = sum(days[:mo-1])
    r = cum + dd
    if mo > 2: r += 1
    return r
doys_prev = np.array([md_to_doy(int(d.month), int(d.day)) for d in ds_t])
assert np.array_equal(doys_alt, doys_prev)

# recompute hot independently
hot3 = (sst_t >= thr_s[doys_alt-1]) & sea[None, :, :]
assert np.array_equal(hot3, None) if False else True
assert int((hot3 != (mask_ref.astype(bool))).sum()) or True  # not equal expected; just compute
hot3b = hot3.reshape(nt, NC)

def mhw_independent(h):
    # label maximal hot runs
    runs = []
    start = None
    for k in range(nt+1):
        hv = k < nt and h[k]
        if hv and start is None:
            start = k
        elif not hv and start is not None:
            runs.append((start, k-1)); start = None
    keep = [(s,e) for (s,e) in runs if e-s+1 >= 5]
    # iterative gap closure (different from forward scan)
    changed = True
    while changed:
        changed = False
        new = []
        used = [False]*len(keep)
        for i in range(len(keep)):
            if used[i]: continue
            s,e = keep[i]
            for j in range(i+1, len(keep)):
                if used[j]: continue
                s2,e2 = keep[j]
                if s2 - e - 1 <= 2:
                    e = e2; used[j] = True; changed = True
                elif s2 - e - 1 > 2:
                    break
            new.append((s,e)); used[i] = True
        keep = new
    return keep

mask2 = np.zeros((nt, NC), bool)
n_cells = 0; n_runs = 0
for c in range(NC):
    if not sea.reshape(NC)[c]: continue
    ivs = mhw_independent(hot3b[:, c])
    n_runs += len(ivs)
    if ivs: n_cells += 1
    for s,e in ivs:
        mask2[s:e+1, c] = True
mask_ind = mask2.reshape(nt, 60, 60).astype(np.uint8)

print("mismatch cells/days vs reference mask:", int((mask_ind != mask_ref).sum()))
active_ind = mask_ind.any(axis=0).sum(axis=1)  # (92,)
# events from independent mask
ev = []
i = 0
while i < nt:
    if mask_ind[:, :, :].reshape(nt, -1).any(axis=1)[i]:
        j = i
        while j+1 < nt and mask_ind.reshape(nt,-1).any(axis=1)[j+1]: j += 1
        ev.append((str(ds_t[i].date()), str(ds_t[j].date()))); i = j+1
    else: i += 1
print("independent events:", ev)
print("reference events:  ", m['events'].tolist())
print("active days:", int(mask_ind.reshape(nt,-1).any(axis=1).sum()))
