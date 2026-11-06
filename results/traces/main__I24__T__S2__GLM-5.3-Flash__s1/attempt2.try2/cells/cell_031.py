import numpy as np, pickle, datetime as dt

hot = np.load("/work/hot.npy"); mhw = np.load("/work/mhw.npy"); sea = np.load("/work/sea.npy")
with open("/work/dates_ext_tgt.pkl","rb") as fh: dd = pickle.load(fh)
tgt_dates = dd["tgt_dates"]
with open("/work/events.pkl","rb") as fh: ev = pickle.load(fh)

# distribution of per-cell onsets/ends
onsets = np.array([s for evs in ev["percell"].values() for s, e in evs])
ends = np.array([e for evs in ev["percell"].values() for s, e in evs])
uo, co = np.unique(onsets, return_counts=True); ue, ce = np.unique(ends, return_counts=True)
print("onset day-index -> date -> count:")
for i, c in zip(uo, co): print("  ", i, str(tgt_dates[i])[:10], c)
print("end day-index -> date -> count:")
for i, c in zip(ue, ce): print("  ", i, str(tgt_dates[i])[:10], c)

# check mhw mask consistency: recompute active from percell events
act2 = np.zeros(92, dtype=bool)
for s, e in ev["percell"].values():
    act2[s:e+1] = True
print("active recheck:", np.array_equal(act2, mhw.max(axis=(1,2)).astype(bool)))

# independent fresh hot-mask recomputation for 3 sample cells
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
for _ in range(3):
    i, j = sea_cells[rng.integers(len(sea_cells))]
    h2 = np.array([tgt[t, i, j] >= thresh_s[doys[t]-1, i, j] for t in range(92)])
    if not np.array_equal(h2, hot[:, i, j]): ok = False; print("HOT MISMATCH at", i, j)
print("independent hot recheck (3 cells):", "OK" if ok else "FAIL")

# sample cell series around the event: cell at middle of event
i, j = 30, 30
t_lo, t_hi = 55, 80  # around Aug
print(f"\ncell (30,30) SST vs threshold d55..d80 ({str(tgt_dates[55])[:10]}..{str(tgt_dates[80])[:10]}):")
for t in range(t_lo, t_hi):
    sst = tgt[t, i, j]; th = thresh_s[doys[t]-1, i, j]
    print(f"  {str(tgt_dates[t])[:10]} doy={doys[t]} sst={sst:7.3f} thr={th:7.3f} hot={int(hot[t,i,j])} mhw={mhw[t,i,j]}")
