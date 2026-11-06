import numpy as np, pickle
from datetime import date, timedelta

M = np.load("/tmp/M.npy")
with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
with open("/tmp/thr.pkl","rb") as f: T = pickle.load(f)

time_pool = D["time_pool"]
pool_start = date(1991,12,27)
pool_dates = [pool_start + timedelta(days=i) for i in range(len(time_pool))]

# dates selected for d=153
sel = np.where(M[152])[0]
print("n sel:", len(sel))
print("first 15 dates:", [str(pool_dates[i]) for i in sel[:15]])
print("last 5 dates:", [str(pool_dates[i]) for i in sel[-5:]])

# pick a sea cell, e.g. index 0 in cell_idx
cell_idx = T["cell_idx"]
c = int(cell_idx[0])
i, j = divmod(c, 60)
print("cell (i,j):", i, j, "lat/lon:", D["lat"][i], D["lon"][j])

pool2 = D["sst_pool"].reshape(4028, 3600)[:, cell_idx]
vals = pool2[sel, 0]
print("pool SST K for this cell, d=153:", np.round(vals, 2))
print("min/max K:", vals.min(), vals.max(), "-> C:", vals.min()-273.15, vals.max()-273.15)
import numpy as np
print("hazen 90 pct K:", np.nanpercentile(vals, 0.9, method="hazen"), "C:", np.nanpercentile(vals,0.9,method="hazen")-273.15)
print("mean K:", np.nanmean(vals), "C:", np.nanmean(vals)-273.15)
