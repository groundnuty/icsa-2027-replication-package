import xarray as xr, numpy as np, warnings
warnings.filterwarnings('ignore')
ds = xr.open_dataset('/work/data/sst_20040715.nc', engine='h5netcdf')
print(ds.dims, {k: tuple(v.shape) for k,v in ds.variables.items()})
print("lat[0:3]:", ds['latitude'].values[:3], "lat[-3:]:", ds['latitude'].values[-3:])
print("lon[0:3]:", ds['longitude'].values[:3], "lon[-3:]:", ds['longitude'].values[-3:])
a = ds['analysed_sst'].values[0]
print("a shape:", a.shape)
# ASCII map: every 10th point; '#' = finite, '.' = NaN
H, W = a.shape
lines = []
for i in range(0, H, 20):
    row = ""
    for j in range(0, W, 20):
        row += "#" if np.isfinite(a[i, j]) else "."
    lines.append(f"{ds['latitude'].values[i]:6.2f}  {row}")
print("      lon: " + " ".join(f"{v:6.2f}" for v in ds['longitude'].values[0::40]))
for l in lines: print(l)
# known points:
import numpy as np
lat = ds['latitude'].values; lon = ds['longitude'].values
def sample(latv, lonv, name):
    i = int(np.argmin(np.abs(lat - latv))); j = int(np.argmin(np.abs(lon - lonv)))
    print(f"{name}: lat={lat[i]:.3f} lon={lon[j]:.3f} SST={a[i,j]}")
sample(54.87, 14.10, "Bornholm Basin (sea, expect ~290K in Jul2004)")
sample(54.65, 13.35, "Ruegen island (land, expect NaN)")
sample(54.50, 13.60, "Arkona Strait (sea)")
sample(55.50, 18.00, "Gotland (land, expect NaN)")
sample(56.00, 19.00, "Baltic Proper (sea)")
ds.close()
