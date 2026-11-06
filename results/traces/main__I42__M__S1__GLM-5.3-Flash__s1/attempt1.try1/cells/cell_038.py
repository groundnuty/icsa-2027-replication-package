import numpy as np, h5py
from datetime import date, timedelta

sst_t = np.load("/work/sst_target.npy")
thr_s = np.load("/work/thr_smooth2.npy")
MD_CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
doys = np.array([MD_CUM[t.month-1]+t.day for t in target_dates])

# cells adjacent to the MHW cells - check their 4-day runs and near-misses
with h5py.File("/data/icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc","r") as f:
    lat = f["latitude"][:]; lon = f["longitude"][:]
i0 = 435; j0 = 485
hot = (sst_t >= thr_s[doys-1])
sea_mask = np.isfinite(sst_t).all(axis=0)

mhw = np.load("/work/mhw_final.npy")
cells = set(zip(*np.where(mhw.any(axis=0))))
neigh = set()
for (r,c) in cells:
    for dr,dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
        rr, cc = r+dr, c+dc
        if 0 <= rr < 60 and 0 <= cc < 60 and sea_mask[rr,cc] and (rr,cc) not in cells:
            neigh.add((rr,cc))
print("neighbouring sea cells with hot runs but no MHW:", len(neigh))
for (r,c) in sorted(neigh):
    idx = np.where(hot[:,r,c])[0]
    # longest run
    best=0; cur=0
    for v in hot[:,r,c]:
        cur = cur+1 if v else 0
        best = max(best, cur)
    print(f"  cell({r},{c}) lat={lat[i0+r]:.2f} lon={lon[j0+c]:.2f}: hot days {list(map(int,idx))}, longest run {best}")
