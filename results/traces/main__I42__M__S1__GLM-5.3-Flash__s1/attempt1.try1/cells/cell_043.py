import numpy as np, h5py
from datetime import date, timedelta

base = "/data/icsa2027_data_20261101T090944Z/s1z"
with h5py.File(f"{base}/sst_19920615.nc","r") as f:
    lat = f["latitude"][:]; lon = f["longitude"][:]
lat_idx = np.where((lat >= 62.25-1e-6) & (lat <= 63.45+1e-6))[0]
lon_idx = np.where((lon >= 18.73-1e-6) & (lon <= 19.93+1e-6))[0]
i0 = lat_idx[0]; j0 = lon_idx[0]

sst_t = np.load("/work/sst_target_corr.npy").astype(np.float64)
thr_s = np.load("/work/thr_smooth_corr.npy")
mhw = np.load("/work/mhw_final_corr.npy")
MD_CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
doys = np.array([MD_CUM[t.month-1]+t.day for t in target_dates])

cells = sorted(zip(*np.where(mhw.any(axis=0))))
print("MHW cells with (lat, lon):")
for (r,c) in cells:
    print(f"  ({r},{c}) lat={lat[i0+r]:.2f} lon={lon[j0+c]:.2f}")
