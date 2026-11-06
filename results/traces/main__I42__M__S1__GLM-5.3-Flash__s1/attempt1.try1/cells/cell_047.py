import os, numpy as np, xarray as xr, json
print(os.listdir("/work/output"))
print("sizes:", {f: os.path.getsize(f"/work/output/{f}") for f in os.listdir("/work/output")})

# final consistency: mask matches computed events
ds = xr.open_dataset("/work/output/mhw_mask.nc", engine="h5netcdf")
m = ds.mhw.values
active = m.any(axis=(1,2))
import numpy as np
idx = np.where(active)[0]
from datetime import date, timedelta
tds = [date(2012,6,1)+timedelta(days=k) for k in range(92)]
print("active days in written file:", [tds[i].isoformat() for i in idx])
print("per-cell MHW day-cells:", int(m.sum()), "cells involved:", int(m.any(axis=0).sum()))
print("all land/other days zero elsewhere:", int(m.sum()) == m[75:80].sum())
rep = json.load(open("/work/output/report.json"))
print("report keys:", sorted(rep.keys()))
