import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 64.51, 65.71
LON_MIN, LON_MAX = 21.97, 23.17
T_START = dt.date(2019, 6, 1)
T_END = dt.date(2019, 8, 31)
TOL = 1e-4

data = np.load("sst_all.npy")
meta = json.load(open("meta.json"))
nb = meta["nb"]
cells = np.load("cells.npy").tolist()
thr = np.load("thr_t.npy").tolist()
nlat, nlon = data.shape[1:]
ndays = len(meta["days"])
mask = np.zeros((ndays, nlat, nlon), dtype=np.uint8)
nruns = 0
for ci, (r, c) in enumerate(cells):
    ser = data[nb:, r, c].tolist()
    th = thr[ci]
    hot = [ser[k] >= th[k] for k in range(ndays)]
    runs = []
    i = 0
    while i < ndays:
        if hot[i]:
            j = i
            while j + 1 < ndays and hot[j + 1]:
                j += 1
            if j - i + 1 >= 5:
                runs.append((i, j))
            i = j + 1
        else:
            i += 1
    k = 0
    while k < len(runs):
        a, b = runs[k]
        while k + 1 < len(runs) and runs[k + 1][0] - b - 1 <= 2:
            b = runs[k + 1][1]
            k += 1
        mask[a:b + 1, r, c] = 1
        nruns += 1
        k += 1
    if ci % 500 == 0:
        print("cell", ci, "of", len(cells))
print("MHWs", nruns, "in-MHW cell-days", int(mask.sum()))
np.save("mask_full.npy", mask)
