import numpy as np, h5py
from datetime import date, timedelta

base = "/data/icsa2027_data_20261101T090944Z/s1z"
with h5py.File(f"{base}/sst_19920615.nc","r") as f:
    lat = f["latitude"][:]; lon = f["longitude"][:]
lat_idx = np.where((lat >= 62.25-1e-6) & (lat <= 63.45+1e-6))[0]
lon_idx = np.where((lon >= 18.73-1e-6) & (lon <= 19.93+1e-6))[0]
i0, j0 = lat_idx[0], lon_idx[0]
sst_t = np.load("/work/sst_target_corr.npy").astype(np.float64)
thr_s = np.load("/work/thr_smooth_corr.npy")
MD_CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
doys = np.array([MD_CUM[t.month-1]+t.day for t in target_dates])

# print detail for 3 representative MHW cells
for (ii,jj) in [(54,52),(56,53),(59,59)]:
    print(f"cell({ii},{jj}) lat={lat[i0+ii]:.2f} lon={lon[j0+jj]:.2f}:")
    for k in range(75, 80):
        print(f"   {target_dates[k]}: sst={sst_t[k,ii,jj]:.3f} thr={thr_s[doys[k]-1,ii,jj]:.3f} diff={sst_t[k,ii,jj]-thr_s[doys[k]-1,ii,jj]:+.3f}")

# check threshold/percentile spread across the target period for one MHW cell
print("\nthr and sst at cell(56,56) for all 92 days:")
for k in [0, 30, 60, 74, 75, 79, 80, 91]:
    print(f"   {target_dates[k]} (doy {doys[k]}): sst={sst_t[k,56,56]:.3f} thr={thr_s[doys[k]-1,56,56]:.3f}")
