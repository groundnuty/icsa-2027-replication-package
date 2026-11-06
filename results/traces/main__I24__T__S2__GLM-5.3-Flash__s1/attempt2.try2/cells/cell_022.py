import numpy as np, warnings, json, datetime as dt, os, pickle

ext = np.concatenate([np.load(f"/work/parts/{n}.npy") for n in ("ext_a","ext_b","ext_c","ext_d")], axis=0).astype(np.float64)
tgt = np.load("/work/parts/tgt.npy").astype(np.float64)
dates = np.load("/work/dates.npy")
EXT0, EXT1 = 3647, 7674
TGT0, TGT1 = 8187, 8278
ext_dates = dates[EXT0:EXT1+1]
tgt_dates = dates[TGT0:TGT1+1]
assert ext_dates.size == ext.shape[0] and tgt_dates.size == tgt.shape[0]

def doy_of(d64):
    d = d64.astype("datetime64[D]").item()
    y = d.year
    yd = d.timetuple().tm_yday
    leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    if not leap and yd >= 60:
        yd += 1
    return yd

assert doy_of(np.datetime64("1992-02-29")) == 60 and doy_of(np.datetime64("1993-03-01")) == 61
assert doy_of(np.datetime64("1993-02-28")) == 59 and doy_of(np.datetime64("1991-12-31")) == 366
print("doy mapping OK")

# --- sea cells ---
sea = np.all(np.isfinite(tgt), axis=0)
nsea = int(sea.sum())
print("cells:", tgt[0].size, "sea cells:", nsea,
      "never-finite:", int((~np.isfinite(tgt).any(axis=0)).sum()),
      "partial:", int((np.isfinite(tgt).any(axis=0) & ~sea).sum()))
cnt = np.isfinite(tgt).sum(axis=(1,2)); print("target per-day finite min/max:", int(cnt.min()), int(cnt.max()))
cntb = np.isfinite(ext).sum(axis=(1,2)); print("ext per-day finite min/max:", int(cntb.min()), int(cntb.max()))

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

for d in (1, 59, 60, 61, 153, 244, 366):
    print("doy", d, "->", md_of_doy(d))

ext_days = ext_dates.astype("datetime64[D]").astype(int)
masks = {}
pool_sizes = np.zeros(366, dtype=int)
for d in range(1, 367):
    if d == 60:
        masks[d] = None; continue
    m, dd = md_of_doy(d)
    mask = np.zeros(ext_days.size, dtype=bool)
    for y in range(1992, 2003):
        ci = int(np.datetime64(dt.date(y, m, dd)).astype("datetime64[D]").astype(int))
        mask |= (np.abs(ext_days - ci) <= 5)
    masks[d] = mask
    pool_sizes[d-1] = int(mask.sum())

print("pool sizes d1..4:", pool_sizes[:4], "d56..66:", pool_sizes[55:66], "d362..366:", pool_sizes[361:366])
print("min/max pool (excl d60):", int(pool_sizes[pool_sizes>0].min()), int(pool_sizes[pool_sizes>0].max()))
used = np.zeros(ext_days.size, dtype=bool)
for d in range(1, 367):
    if masks[d] is not None: used |= masks[d]
print("ext days used: first", ext_dates[used][0], "last", ext_dates[used][-1], "n_used", int(used.sum()), "/", ext_days.size)

# --- raw threshold + climatology per cell per DOY ---
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    thresh_raw = np.full((366, 60, 60), np.nan, dtype=np.float64)
    clim_raw = np.full((366, 60, 60), np.nan, dtype=np.float64)
    for d in range(1, 367):
        if d == 60: continue
        vals = ext[masks[d]]          # (P, 60, 60)
        vals = vals.reshape(vals.shape[0], -1)
        with np.errstate(invalid="ignore"):
            thresh_raw[d-1] = np.nanquantile(vals, 0.9, axis=0, method="hazen").reshape(60, 60)
            clim_raw[d-1] = np.nanmean(vals, axis=0).reshape(60, 60)

print("raw threshold sample (cell [10,10], doy 150..160):", np.round(thresh_raw[149:160, 10, 10], 4))
print("raw clim sample    (cell [10,10], doy 150..160):", np.round(clim_raw[149:160, 10, 10], 4))
print("threshold nan cells per doy (d150, d244, d366):",
      int(np.isnan(thresh_raw[149]).sum()), int(np.isnan(thresh_raw[243]).sum()), int(np.isnan(thresh_raw[365]).sum()))
print("clim nan cells per doy (d150):", int(np.isnan(clim_raw[149]).sum()))

np.save("/work/thresh_raw.npy", thresh_raw)
np.save("/work/clim_raw.npy", clim_raw)
np.save("/work/sea.npy", sea)
np.save("/work/tgt64.npy", tgt)
np.save("/work/ext64.npy", ext)
with open("/work/masks.pkl","wb") as fh: pickle.dump(masks, fh)
with open("/work/dates_ext_tgt.pkl","wb") as fh: pickle.dump({"ext_dates": ext_dates, "tgt_dates": tgt_dates}, fh)
print("stage B saved; /work:", sorted(os.listdir("/work")))
