import numpy as np, datetime
target = np.load("/tmp/mhw/target.npy")
sea = np.load("/tmp/mhw/sea_cells.npy")
thr_s = np.load("/tmp/mhw/thr_smooth.npy")
full_mask = np.load("/tmp/mhw/full_mask.npy")
sea_idx = np.argwhere(sea)
d0 = datetime.date(2007, 6, 1)
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d): return cum[d.month-1] + d.day
doys = np.array([doy(d0 + datetime.timedelta(days=i)) for i in range(92)])

# find a cell whose mask contains a gap day (mask=1 but not hot) -> proves gap joining
found = False
for ci in range(len(sea_idx)):
    r, c = sea_idx[ci]
    sst = target[:, r, c]
    hot = sst >= thr_s[ci, doys]
    mk = full_mask[:, r, c].astype(bool)
    if mk.any() and (mk & ~hot).any():
        pat = "".join("#" if h else "." for h in hot)
        mpat = "".join("M" if m else "." for m in mk)
        print(f"cell {np.load('/tmp/mhw/lat.npy')[r]}, {np.load('/tmp/mhw/lon.npy')[c]}: MHW days incl gaps")
        print("hot :", pat)
        print("mask:", mpat)
        found = True
        break
if not found:
    print("no cell with gap days; checking a plain MHW cell")
    for ci in range(len(sea_idx)):
        r, c = sea_idx[ci]
        hot = target[:, r, c] >= thr_s[ci, doys]
        mk = full_mask[:, r, c].astype(bool)
        if mk.sum() >= 5:
            print("hot :", "".join("#" if h else "." for h in hot))
            print("mask:", "".join("M" if m else "." for m in mk))
            break
