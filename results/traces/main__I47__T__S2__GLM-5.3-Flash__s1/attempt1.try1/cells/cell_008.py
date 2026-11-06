import numpy as np, datetime as dt, json, os, time, warnings
from numpy.lib.stride_tricks import sliding_window_view
import fsspec, h5py

t_start = time.time()
PATH = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
fs = fsspec.filesystem('onedata')

def fresh_h5():
    return h5py.File(fs.open(PATH, 'rb'), 'r')

def read_with_retry(fn, tries=4, tag=""):
    last = None
    for k in range(tries):
        f = None; hf = None
        try:
            hf = fresh_h5()
            out = fn(hf)
            try: hf.close()
            except Exception: pass
            return out
        except Exception as e:
            last = e
            print(f"  [retry {k+1}] {tag}: {type(e).__name__}: {str(e)[:120]}")
            time.sleep(2 + 2*k)
            try:
                if hf is not None: hf.close()
            except Exception: pass
    raise last

# ---------- metadata ----------
lat, lon, dates = read_with_retry(lambda hf: (hf['latitude'][:], hf['longitude'][:],
        (np.datetime64('1981-01-01') + hf['time'][:].astype('timedelta64[s]')).astype('datetime64[D]')),
        tag="meta")
print("meta ok:", dates[0], dates[-1], len(dates))
assert np.array_equal(np.diff(dates).astype(int), np.ones(len(dates)-1)), "not contiguous daily"

ii = np.where((lat >= np.float32(64.39)) & (lat <= np.float32(65.59)))[0]
jj = np.where((lon >= np.float32(23.41)) & (lon <= np.float32(24.61)))[0]
i0, i1, j0, j1 = int(ii[0]), int(ii[-1])+1, int(jj[0]), int(jj[-1])+1
def idx_of(s): return int((np.datetime64(s) - dates[0]) / np.timedelta64(1, 'D'))
dset_read = lambda a, b: read_with_retry(lambda hf: hf['analysed_sst'][a:b, i0:i1, j0:j1], tag=f"read[{a}:{b}]")

tA, tB = idx_of('2019-06-01'), idx_of('2019-08-31')
arrT = dset_read(tA, tB+1).astype(np.float64)
target_dates = dates[tA:tB+1]; nT = len(target_dates)
print(f"target read: {target_dates[0]}..{target_dates[-1]} ({nT} days) at {time.time()-t_start:.1f}s")

sea2d = np.isfinite(arrT).all(axis=0)
sea = sea2d.ravel(); nsea = int(sea.sum())
print(f"sea cells: {nsea} / {sea.size}")

eA, eB = idx_of('1991-12-27'), idx_of('2003-01-05')
arr44 = dset_read(eA, eB+1).astype(np.float64)
ext_dates = dates[eA:eB+1]
print(f"baseline read: {ext_dates[0]}..{ext_dates[-1]} ({len(ext_dates)} days) at {time.time()-t_start:.1f}s")

CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def mdoy(dd):
    months = dd.astype('datetime64[M]').astype(int) % 12 + 1
    days = (dd - dd.astype('datetime64[M]')).astype('timedelta64[D]').astype(int) + 1
    return CUM[months-1] + days

# ---------- pools ----------
arr44_sea = arr44.reshape(len(ext_dates), -1)[:, sea]
del arr44
doy_ext = mdoy(ext_dates)
nlon = len(jj)
thr_raw = np.full((366, nsea), np.nan)
clim_raw = np.full((366, nsea), np.nan)
pool_counts = np.zeros(366, int); nanpool = np.zeros(366, int)
cols = np.arange(nsea)

for d in range(1, 367):
    if d == 60: continue
    idx = np.nonzero(np.abs(doy_ext - d) <= 5)[0]
    pool = arr44_sea[idx]
    pool_counts[d-1] = len(idx)
    s = np.sort(pool, axis=0)
    n = np.count_nonzero(np.isfinite(pool), axis=0)
    nanpool[d-1] = int((n == 0).sum())
    v = 0.9*n - 0.5
    nmax = np.maximum(n-1, 0)
    lo = np.clip(np.floor(v).astype(np.int64), 0, nmax)
    hi = np.minimum(lo+1, nmax)
    site_g = v - np.floor(v)
    q = s[lo, cols] + site_g*(s[hi, cols] - s[lo, cols])
    q[n == 0] = np.nan
    thr_raw[d-1] = q
    with np.errstate(invalid='ignore'):
        clim_raw[d-1] = np.nanmean(pool, axis=0)

for A in (thr_raw, clim_raw):
    A[59] = 0.5*(A[58] + A[60])
print(f"pools done at {time.time()-t_start:.1f}s; pool sizes min/max "
      f"{pool_counts[pool_counts>0].min()}/{pool_counts.max()}; all-NaN pools per doy: {nanpool}")
with np.errstate(invalid='ignore'), warnings.catch_warnings():
    warnings.simplefilter("ignore")
    idx = np.nonzero(np.abs(doy_ext - 200) <= 5)[0]
    ref = np.nanquantile(arr44_sea[idx], 0.9, axis=0, method='hazen')
print("in-situ hazen vs numpy max|diff|:", np.nanmax(np.abs(thr_raw[199] - ref)))

def circ31(x):
    xp = np.concatenate([x[-15:], x, x[:15]], axis=0)
    return sliding_window_view(xp, 31, axis=0).mean(axis=-1)
thr = circ31(thr_raw); clim = circ31(clim_raw)
print(f"smoothed at {time.time()-t_start:.1f}s; NaNs: thr {int(np.isnan(thr).sum())}, clim {int(np.isnan(clim).sum())}")

# ---------- hot days / per-cell MHW ----------
doy_t = mdoy(target_dates)
sst = arrT.reshape(nT, -1)[:, sea]
hot = sst >= thr[doy_t - 1]
print(f"hot cell-days: {int(hot.sum())} / {hot.size}")

def cell_mhw(hotmat):
    T, N = hotmat.shape
    z = np.zeros((T+2, N), np.int8); z[1:-1] = hotmat
    dz = z[1:] - z[:-1]
    out = np.zeros((T, N), bool); total = 0
    for c in range(N):
        col = dz[:, c]
        ss = np.nonzero(col == 1)[0]; ee = np.nonzero(col == -1)[0]
        ivals = [[a, b-1] for a, b in zip(ss, ee)]
        ivals = [iv for iv in ivals if iv[1]-iv[0]+1 >= 5]
        merged = []
        for a, b in ivals:
            if merged and a - merged[-1][1] - 1 <= 2: merged[-1][1] = b
            else: merged.append([a, b])
        for a, b in merged:
            out[a:b+1, c] = True; total += 1
    return out, total

mhw_sea, n_cell_mhw = cell_mhw(hot)
print(f"per-cell MHWs: {n_cell_mhw}; MHW cell-days: {int(mhw_sea.sum())}")

active = mhw_sea.any(axis=1)
print(f"active days: {int(active.sum())} / {nT}")
events = []
i = 0
while i < nT:
    if active[i]:
        j = i
        while j+1 < nT and active[j+1]: j += 1
        events.append((i, j)); i = j+1
    else: i += 1
print("regional events:", len(events))
for a, b in events:
    print(f"  {target_dates[a]} .. {target_dates[b]} ({b-a+1}d)")

mhw_full = np.zeros((nT, sea.size), np.uint8)
mhw_full[:, sea] = mhw_sea.astype(np.uint8)
mhw_full = mhw_full.reshape(nT, len(ii), len(jj))
np.save('/tmp/mhw.npy', mhw_full)
np.save('/tmp/idxmeta.npy', np.array([i0, i1, j0, j1, nT, nsea], dtype=np.int64))
with open('/tmp/events.json', 'w') as fh:
    json.dump([[str(target_dates[a]), str(target_dates[b])] for a, b in events], fh)
for k in (0, nT//2, nT-1):
    d0 = doy_t[k]-1
    print(f"  {target_dates[k]} doy {doy_t[k]}: clim {np.nanmean(clim[d0]):.3f} thr {np.nanmean(thr[d0]):.3f} "
          f"sst {np.nanmean(sst[k]):.3f} hot {int(hot[k].sum())} mhw {int(mhw_sea[k].sum())}")
print(f"TOTAL {time.time()-t_start:.1f}s")
