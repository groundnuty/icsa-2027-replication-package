import numpy as np, pickle

hot = np.load("/work/hot.npy"); mhw = np.load("/work/mhw.npy"); sea = np.load("/work/sea.npy")
with open("/work/dates_ext_tgt.pkl","rb") as fh: dd = pickle.load(fh)
tgt_dates = dd["tgt_dates"]
with open("/work/events.pkl","rb") as fh: ev = pickle.load(fh)

# active-day recheck from per-cell events
act2 = np.zeros(92, dtype=bool)
for evs in ev["percell"].values():
    for s, e in evs:
        act2[s:e+1] = True
print("active recheck:", np.array_equal(act2, mhw.max(axis=(1,2)).astype(bool)))

# per-cell MHWs each exactly one per cell? any cell with >1?
multi = {k: len(v) for k, v in ev["percell"].items() if len(v) != 1}
print("cells with !=1 MHW:", len(multi))

# independent fresh hot-mask recomputation for 5 random sea cells
thresh_s = np.load("/work/thresh_s.npy"); tgt = np.load("/work/tgt64.npy")
def doy_of(d64):
    d = d64.astype("datetime64[D]").item(); y = d.year
    yd = d.timetuple().tm_yday
    leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    if not leap and yd >= 60: yd += 1
    return yd
doys = np.array([doy_of(d) for d in tgt_dates])
rng = np.random.default_rng(42)
sea_cells = np.argwhere(sea)
ok = True
for _ in range(5):
    i, j = sea_cells[rng.integers(len(sea_cells))]
    h2 = np.array([bool(tgt[t, i, j] >= thresh_s[doys[t]-1, i, j]) for t in range(92)])
    if not np.array_equal(h2, hot[:, i, j]): ok = False; print("HOT MISMATCH at", i, j)
print("independent hot recheck (5 cells):", "OK" if ok else "FAIL")

# sample cell series around the event
i, j = 30, 30
print(f"\ncell (30,30) {str(tgt_dates[60])[:10]}..{str(tgt_dates[80])[:10]}:")
for t in range(60, 81):
    sst = tgt[t, i, j]; th = thresh_s[doys[t]-1, i, j]
    print(f"  {str(tgt_dates[t])[:10]} doy={doys[t]:3d} sst={sst:7.3f} thr={th:7.3f} hot={int(hot[t,i,j])} mhw={mhw[t,i,j]}")
