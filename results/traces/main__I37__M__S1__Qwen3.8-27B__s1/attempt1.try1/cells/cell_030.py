import os, time, hashlib, json, datetime as dt
import numpy as np, h5py

t0 = time.time()
# --- load & verify ---
ext = np.load('/work/chk/ext.npy').astype(np.float64)   # (4028,60,60) 1991-12-27..2003-01-05
tgt = np.load('/work/chk/tgt.npy').astype(np.float64)   # (92,60,60)   2012-06-01..2012-08-31
he = hashlib.sha256(np.ascontiguousarray(ext.astype(np.float32)).tobytes()).hexdigest()
ht = hashlib.sha256(np.ascontiguousarray(tgt.astype(np.float32)).tobytes()).hexdigest()
want = dict(l.strip().split() for l in open('/work/chk/hashes.txt'))
assert want['ext'] == he, "ext hash mismatch"
assert want['tgt'] == ht, "tgt hash mismatch"
print("hashes OK")

base = "/data/icsa2027_data_20261101T090944Z/s1z"
def src_row(ymd):
    with h5py.File(f"{base}/sst_{ymd}.nc", 'r') as f:
        return f['analysed_sst'][0, 330:390, 551:611].astype(np.float32)
okc = 0
for idx, ymd in {0:'19911227', 5:'19920101', 1000:'19940629', 2000:'19970714', 3000:'20000726', 4022:'20021231', 4027:'20030105'}.items():
    assert np.array_equal(ext[idx], src_row(ymd), equal_nan=True), f"ext row {idx}"
    okc += 1
for idx, ymd in {0:'20120601', 45:'20120716', 91:'20120831'}.items():
    assert np.array_equal(tgt[idx], src_row(ymd), equal_nan=True), f"tgt row {idx}"
    okc += 1
print("source spot-checks OK:", okc)

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
tgt_dates = daterange(dt.date(2012,6,1), dt.date(2012,8,31))
assert len(ext_dates) == 4028 and len(tgt_dates) == 92

def doy_map(d):
    return dt.date(2000, d.month, d.day).timetuple().tm_yday
doy_ext = np.array([doy_map(d) for d in ext_dates])
doy_tgt = np.array([doy_map(d) for d in tgt_dates])
doy_b = doy_ext[5:5+4018]
print("doy_b first/last:", doy_b[:3], doy_b[-3:])

# hazen sanity
q_h = np.quantile(np.arange(1, 11), 0.9, method='hazen')
print("hazen check (expect 10.0):", q_h)

# --- sea cells ---
finite_tgt = np.isfinite(tgt)
sea = finite_tgt.all(axis=0)
n_sea = int(sea.sum())
print("sea cells:", n_sea, "/", sea.size)

# --- pools, threshold, climatology ---
N, CLAT, CLON = ext.shape
thr_raw = np.full((366, CLAT, CLON), np.nan)
clim_raw = np.full((366, CLAT, CLON), np.nan)
nvalid_min = np.full((366,), 10**9, dtype=int)
for d in range(1, 367):
    if d == 60:
        continue
    js = np.where(doy_b == d)[0]
    assert len(js) == 11, (d, len(js))
    rows = (5 + js[:, None] + np.arange(-5, 6)[None, :]).ravel()
    pool = ext[rows]                      # (121, 60, 60)
    nv = np.isfinite(pool).sum(axis=0)
    nvalid_min[d-1] = int(nv.min())
    thr_raw[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clim_raw[d-1] = np.nanmean(pool, axis=0)
thr_raw[59] = 0.5 * (thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5 * (clim_raw[58] + clim_raw[60])
print("min pool size over d,cells:", int(nvalid_min.min()), "max:", int(nvalid_min.max()))

def smooth31(a):  # (366, ...) wrapped centred 31-day mean
    acc = np.zeros_like(a)
    for k in range(-15, 16):
        acc += np.roll(a, -k, axis=0)
    return acc / 31.0

thr = smooth31(thr_raw)
clim = smooth31(clim_raw)
# verify wrap with a direct loop on one cell
c = (10, 12)
ref = np.array([np.mean([thr_raw[(d + k) % 366, c[0], c[1]] for k in range(-15, 16)]) for d in range(366)])
print("smoothing check max diff:", np.abs(thr[:, c[0], c[1]] - ref).max())
print("thr range:", np.nanmin(thr), np.nanmax(thr))
print("clim range:", np.nanmin(clim), np.nanmax(clim))
np.save('/work/chk/thr.npy', thr); np.save('/work/chk/clim.npy', clim)
np.save('/work/chk/sea.npy', sea)
json.dump({'doy_tgt': doy_tgt.tolist()}, open('/work/chk/doy_tgt.json','w'))
print("compute stage 1 done in", time.time()-t0)
