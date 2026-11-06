import numpy as np, warnings, json, datetime as dt, os

ext = np.concatenate([np.load(f"/work/parts/{n}.npy") for n in ("ext_a","ext_b","ext_c","ext_d")], axis=0).astype(np.float64)
tgt = np.load("/work/parts/tgt.npy").astype(np.float64)
dates = np.load("/work/dates.npy")
print("ext:", ext.shape, ext.dtype, "tgt:", tgt.shape, "dates:", dates[0], dates[-1])
EXT0, EXT1 = 3647, 7674
TGT0, TGT1 = 8187, 8278
assert dates[EXT0] == np.datetime64("1991-12-27") and dates[EXT1] == np.datetime64("2003-01-05")
assert dates[TGT0] == np.datetime64("2004-06-01") and dates[TGT1] == np.datetime64("2004-08-31")
ext_dates = dates[EXT0:EXT1+1]
assert ext_dates.size == ext.shape[0] and (TGT1-TGT0+1) == tgt.shape[0]

# --- day-of-year mapping (1..366; Feb29=d60; non-leap years skip 60) ---
def doy_of(d64):
    d = d64.astype("datetime64[D]").item()
    y = d.year
    yd = d.timetuple().tm_yday
    leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    if not leap and yd >= 60:
        yd += 1
    return yd

checks = {"1992-02-28":59, "1992-02-29":60, "1992-03-01":61, "1991-12-31":366,
          "1993-03-01":61, "1993-02-28":59, "2004-06-01":153, "2004-08-31":244,
          "2000-02-29":60, "2000-03-01":61, "1992-01-01":1, "2004-02-29":60}
for s, v in checks.items():
    got = doy_of(np.datetime64(s))
    assert got == v, (s, got, v)
print("doy mapping OK")

# hazen sanity
assert np.quantile(np.arange(1., 11.), 0.5, method="hazen") == 5.5
assert abs(np.quantile(np.array([1.,2,3,4]), 0.9, method="hazen") - 3.1) < 1e-12
print("hazen OK")

# --- sea cells ---
sea = np.all(np.isfinite(tgt), axis=0)
partial = np.isfinite(tgt).any(axis=0) & ~sea
nsea = int(sea.sum())
print("cells:", tgt[0].size, "sea cells:", nsea, "never-finite:", int((~np.isfinite(tgt).any(axis=0)).sum()), "partial:", int(partial.sum()))
print("target per-day finite count min/max:", int(np.isfinite(tgt).sum(axis=(1,2)).min()), int(np.isfinite(tgt).sum(axis=(1,2)).max()))
print("ext per-day finite count min/max:", int(np.isfinite(ext).sum(axis=(1,2)).min()), int(np.isfinite(ext).sum(axis=(1,2)).max()))

# --- md_of_doy ---
def md_of_doy(d):
    if d <= 31: return (1, d)
    if d <= 59: return (2, d-31)
    if d == 60: return (2, 29)
    if d <= 91: return (3, d-60)
    if d <= 121: return (4, d-91)
    if d <= 152: return (5, d-121)
    if d <= 182: return (6, d-152)
    if d <= 213: return (7, d-182)
    if d <= 244: return (8, d-213)
    if d <= 274: return (9, d-244)
    if d <= 305: return (10, d-274)
    if d <= 335: return (11, d-305)
    return (12, d-335)

for d in (1, 28, 59, 60, 61, 153, 244, 366):
    print("doy", d, "->", md_of_doy(d))

ext_days = ext_dates.astype("datetime64[D]").astype(int)
masks = {}
pool_sizes = np.zeros(366, dtype=int)
for d in range(1, 367):
    if d == 60:
        masks[d] = None
        continue
    m, dd = md_of_doy(d)
    mask = np.zeros(ext_days.size, dtype=bool)
    for y in range(1992, 2003):
        c = np.datetime64(dt.date(y, m, dd))
        ci = int(c.astype("datetime64[D]").astype(int))
        mask |= (np.abs(ext_days - ci) <= 5)
    masks[d] = mask
    pool_sizes[d-1] = int(mask.sum())

print("pool sizes d1..4:", pool_sizes[:4], "d56..66:", pool_sizes[55:66], "d362..366:", pool_sizes[361:366])
print("min/max pool size (excl d60):", int(pool_sizes[pool_sizes>0].min()), int(pool_sizes[pool_sizes>0].max()))
print("d60 pool size:", int(pool_sizes[59]))

used = np.zeros(ext_days.size, dtype=bool)
for d in range(1, 367):
    if masks[d] is not None: used |= masks[d]
print("ext days used: first", ext_dates[used][0], "last", ext_dates[used][-1], "n_used", int(used.sum()), "of", ext_days.size)

np.savez_compressed("/work/stageA.npz", ext=ext.astype(np.float32), tgt=tgt.astype(np.float32), sea=sea)
import pickle
with open("/work/masks.pkl","wb") as fh: pickle.dump(masks, fh)
print("stage A artifacts saved; /work contents:", sorted(os.listdir("/work")))
