import numpy as np
thr = np.load("/work/thr_raw.npy"); clim = np.load("/work/clim_raw.npy")
cell_allnan = np.isnan(thr).all(axis=0)  # land cells (226)
sea_thr = thr[:, ~cell_allnan]
# For sea cells: NaN frac per doy (should be tiny)
nancount_per_doy = np.isnan(sea_thr).sum(axis=1)  # (366,)
print("max NaN count per doy (sea cells):", nancount_per_doy.max(), "at doy", np.argmax(nancount_per_doy)+1)
print("NaN count at doy 60:", nancount_per_doy[59], "of", sea_thr.shape[1])
print("NaN count at other doys (max excluding 60):", np.delete(nancount_per_doy, 59).max())
# So day 60 is the ONLY doy where sea cells have NaN in the raw thr (pool empty)
# Also check per-sea-cell NaN count excluding doy 60
per_cell = np.delete(np.isnan(sea_thr), 59, axis=0).sum(axis=0)
print("per-cell NaN count excl d60: max", per_cell.max())
