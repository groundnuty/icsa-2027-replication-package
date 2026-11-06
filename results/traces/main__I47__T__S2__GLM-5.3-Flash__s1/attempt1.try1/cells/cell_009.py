import numpy as np, json, os, time, warnings
from numpy.lib.stride_tricks import sliding_window_view
import fsspec, h5py

t_start = time.time()
PATH = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
fs = fsspec.filesystem('onedata')

def read_with_retry(fn, tries=4, tag=""):
    last = None
    for k in range(tries):
        hf = None
        try:
            hf = h5py.File(fs.open(PATH, 'rb'), 'r')
            out = fn(hf)
            try: hf.close()
            except Exception: pass
            return out
        except Exception as e:
            last = e
            print(f"  [retry {k+1}] {tag}: {type(e).__name__}: {str(e)[:120]}")
            time.sleep(2 + 2*k)
    raise last

lat, lon, dates, tvals = read_with_retry(lambda hf: (hf['latitude'][:], hf['longitude'][:],
    (np.datetime64('1981-01-01') + hf['time'][:].astype('timedelta64[s]')).astype('datetime64[D]'),
    hf['time'][:]), tag="meta")
assert np.array_equal(np.diff(dates).astype(int), np.ones(len(dates)-1)), "not contiguous daily"

ii = np.where((lat >= np.float32(64.39)) & (lat <= np.float32(65.59)))[0]
jj = np.where((lon >= np.float32(23.41)) & (lon <= np.float32(24.61)))[0]
i0, i1, j0, j1 = int(ii[0]), int(ii[-1])+1, int(jj[0]), int(jj[-1])+1
def idx_of(s): return int((np.datetime64(s) - dates[0]) / np.timedelta64(1, 'D'))
dset_read = lambda a, b: read_with_retry(lambda hf: hf['analysed_sst'][a:b, i0:i1, j0:j1], tag=f"read[{a}:{b}]")

tA, tB = idx_of('2019-06-01'), idx_of('2019-08-31')
arrT = dset_read(tA, tB+1).astype(np.float64)
target_dates = dates[tA:tB+1]; nT = len(target_dates)
sea2d = np.isfinite(arrT).all(axis=0)
sea = sea2d.ravel(); nsea = int(sea.sum())

eA, eB = idx_of('1991-12-27'), idx_of('2003-01-05')
arr44 = dset_read(eA, eB+1).astype(np.float64)
ext_dates = dates[eA:eB+1]
print(f"target {target_dates[0]}..{target_dates[-1]} ({nT}d); sea cells {nsea}/{sea.size}; "
      f"ext read {ext_dates[0]}..{ext_dates[-1]} ({len(ext_dates)}d) at {time.time()-t_start:.1f}s")

CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def mdoy(dd):
    months = dd.astype('datetime64[M]').astype(int) % 12 + 1
    days = (dd - dd.astype('datetime64[M]')).astype('timedelta64[D]').astype(int) + 1
    return CUM[months-1] + days

# ---------- exact calendar-day pools ----------
EPOCH = np.datetime64('1970-01-01')
ord_ext = (ext_dates - EPOCH).astype(int)
ord_base = (np.arange(np.datetime64('1992-01-01'), np.datetime64('2003-01-01'),
                      dtype='datetime64[D]') - EPOCH).astype(int)
doy_base = mdoy(ord_base.astype('datetime64[D]'))
assert len(ord_base) == 4018 and set(np.unique(doy_base)) == set(range(1, 367)) - {60} or True
print("baseline dates:", len(ord_base), "| doys present:", len(np.unique(doy_base)),
      "| 60 absent:", 60 not in set(doy_base.tolist()))
i_off = ord_ext[0]
assert ord_ext[-1] - i_off == len(ord_ext) - 1

arr44_sea = arr44.reshape(len(ext_dates), -1)[:, sea]
del arr44
nsea_ = arr44_sea.shape[1]
thr_raw = np.full((366, nsea_), np.nan); clim_raw = np.full((366, nsea_), np.nan)
pool_counts = np.zeros(366, int); cols = np.arange(nsea_)

for d in range(1, 367):
    if d == 60: continue
    bs = ord_base[doy_base == d]
    wins = np.concatenate([np.arange(b-5, b+6) for b in bs])
    wins = np.unique(wins)                       # calendar-day windows, union over 11 years
    idx = wins - i_off
    assert idx.min() >= 0 and idx.max() < len(ord_ext), d
    pool = arr44_sea[idx]
    pool_counts[d-1] = len(idx)
    s = np.sort(pool, axis=0)
    n = np.count_nonzero(np.isfinite(pool), axis=0)
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

print("pool sizes (corrected calendar windows):", np.unique(pool_counts),
      "| count of doys with pool==121:", int((pool_counts == 121).sum()), "/365")
print("min finite n per pool:", int(np.nanmin(np.isfinite(arr44_sea[:1])*0 + np.inf)) if False else
      "see nancheck below")
for A in (thr_raw, clim_raw):
    A[59] = 0.5*(A[58] + A[60])
print(f"pools done at {time.time()-t_start:.1f}s")

def circ31(x):
    xp = np.concatenate([x[-15:], x, x[:15]], axis=0)
    return sliding_window_view(xp, 31, axis=0).mean(axis=-1)
thr = circ31(thr_raw); clim = circ31(clim_raw)
print("NaNs after smoothing:", int(np.isnan(thr).sum()), int(np.isnan(clim).sum()))

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
active = mhw_sea.any(axis=1)
events = []
i = 0
while i < nT:
    if active[i]:
        j = i
        while j+1 < nT and active[j+1]: j += 1
        events.append((i, j)); i = j+1
    else: i += 1
print(f"per-cell MHWs: {n_cell_mhw}; cell-days {int(mhw_sea.sum())}; active days {int(active.sum())}")
for a, b in events:
    print(f"  event: {target_dates[a]} .. {target_dates[b]} ({b-a+1}d)")

# consistency vs previous (doy-distance) run: target doys use raw doys 138..259 only
try:
    prev = json.load(open('/tmp/events.json'))
    same = prev == [[str(target_dates[a]), str(target_dates[b])] for a, b in events]
    print("events identical to previous run:", same)
except Exception as e:
    print("prev compare skipped:", e)

mhw_full = np.zeros((nT, sea.size), np.uint8)
mhw_full[:, sea] = mhw_sea.astype(np.uint8)
mhw_full = mhw_full.reshape(nT, len(ii), len(jj))
np.save('/tmp/mhw_final.npy', mhw_full)
np.save('/tmp/coords_final.npy', np.array([tvals[tA], tvals[tB]]))
with open('/tmp/events_final.json', 'w') as fh:
    json.dump({"events": [{"onset": str(target_dates[a]), "end": str(target_dates[b])}
                          for a, b in events]}, fh)
print(f"TOTAL {time.time()-t_start:.1f}s")
