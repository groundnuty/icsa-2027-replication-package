import numpy as np, warnings, json, datetime as dt

ext = np.concatenate([np.load(f"/work/parts/{n}") for n in ("ext_a","ext_b","ext_c","ext_d")], axis=0).astype(np.float64)
tgt = np.load("/work/parts/tgt.npy").astype(np.float64)
dates = np.load("/work/dates.npy")
print("ext:", ext.shape, ext.dtype, "tgt:", tgt.shape, "dates:", dates[0], dates[-1])
EXT0, EXT1 = 3647, 7674   # 1991-12-27 .. 2003-01-05
TGT0, TGT1 = 8187, 8278   # 2004-06-01 .. 2004-08-31
assert dates[EXT0] == np.datetime64("1991-12-27") and dates[EXT1] == np.datetime64("2003-01-05")
assert dates[TGT0] == np.datetime64("2004-06-01") and dates[TGT1] == np.datetime64("2004-08-31")
ext_dates = dates[EXT0:EXT1+1]
tgt_dates = dates[TGT0:TGT1+1]
assert ext_dates.size == ext.shape[0] and tgt_dates.size == tgt.shape[0]

# --- day-of-year mapping (1..366 by month/day; non-leap years skip 60) ---
def doy_of(d64):
    d = d64.astype("datetime64[D]").item()  # python date
    y = d.year
    yd = d.timetuple().tm_yday
    leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    if not leap and yd >= 60:
        yd += 1
    return yd

# sanity of mapping
checks = {("1992-02-28"):59, ("1992-02-29"):60, ("1992-03-01"):61, ("1991-12-31"):366,
          ("1993-03-01"):61, ("1993-02-28"):59, ("2004-06-01"):153, ("2004-08-31"):244,
          ("2000-02-29"):60, ("2000-03-01"):61, ("1992-01-01"):1, ("2004-02-29"):60}
for s, v in checks.items():
    got = doy_of(np.datetime64(s))
    assert got == v, (s, got, v)
print("doy mapping OK")

# --- hazen sanity vs MATLAB default ---
q = np.quantile(np.arange(1., 11.), 0.5, method="hazen")
assert q == 5.5, q
q2 = np.quantile(np.array([1.,2,3,4]), 0.9, method="hazen")  # h=4*0.9+0.5=4.1 -> 3 + 0.1*(4-3)
assert abs(q2 - 3.1) < 1e-12, q2
print("hazen OK:", q, q2)

# --- sea cells: finite on every target day ---
sea = np.all(np.isfinite(tgt), axis=0)            # (60,60)
partial = np.isfinite(tgt).any(axis=0) & ~sea      # some but not all target days finite
nsea = int(sea.sum())
print("cells total:", tgt[0].size, "sea cells (finite all target days):", nsea,
      "never-finite:", int((~np.isfinite(tgt).any(axis=0)).sum()), "partial:", int(partial.sum()))

# per-day finite counts in target (constancy check)
cnt = np.isfinite(tgt).sum(axis=(1,2))
print("target finite-count per day: min/max:", cnt.min(), cnt.max())
cntb = np.isfinite(ext).sum(axis=(1,2))
print("ext finite-count per day: min/max:", cntb.min(), cntb.max())

# --- pool masks per DOY ---
def md_of_doy(d):
    """(month, day) for day-of-year d under the 1..366 mapping (Feb29=d60)."""
    cum = [0,31,59,60,91,121,152,182,213,244,274,305,335,366]
    # months: Jan..Dec boundaries for non-leap-like mapping with Feb29 slot
    # month lengths in the mapping: Jan 31, Feb 28 (59) + Feb29 (60), Mar 31...
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

ext_days = ext_dates.astype("datetime64[D]").astype(int)  # days since epoch
pool_sizes = np.zeros(366, dtype=int)
masks = {}
for d in range(1, 367):
    if d == 60:
        masks[d] = None
        continue
    m, dd = md_of_doy(d)
    mask = np.zeros(ext_days.size, dtype=bool)
    for y in range(1992, 2003):
        c = np.datetime64(dt.date(y, m, dd))
        ci = int(c.astype("datetime64[D]").astype(int))
        mask |= np.abs(ext_days - ci) <= 5
    masks[d] = mask
    pool_sizes[d-1] = int(mask.sum())
print("pool sizes: d1..5:", pool_sizes[:5], " d56..66:", pool_sizes[55:66], " d152..156:", pool_sizes[151:156], " d362..366:", pool_sizes[361:366])
print("min/max pool size (excl d60):", pool_sizes[pool_sizes>0].min(), pool_sizes[pool_sizes>0].max())
print("d60 pool size:", pool_sizes[59])

# which ext days are used by at least one pool
used = np.zeros(ext_days.size, dtype=bool)
for d in range(1, 367):
    if masks[d] is not None: used |= masks[d]
first_used, last_used = ext_dates[used][0], ext_dates[used][-1]
print("ext days used: first", first_used, "last", last_used, "n_used", int(used.sum()), "of", ext_days.size)
np.savez_compressed("/work/stageA.npz", ext=ext.astype(np.float32), tgt=tgt.astype(np.float32),
                    sea=sea, pool_sizes=pool_sizes)
import pickle
with open("/work/masks.pkl","wb") as fh: pickle.dump(masks, fh)
print("stage A artifacts saved")
