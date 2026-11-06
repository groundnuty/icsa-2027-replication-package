import xarray as xr, numpy as np, datetime

# check coordinates identical across a few files and time matches filename
import glob, re
files = sorted(glob.glob('/work/data/sst_*.nc'))
print("local files:", len(files))
ref = xr.open_dataset(files[0], engine='h5netcdf')
lat_ref = ref.latitude.values.copy(); lon_ref = ref.longitude.values.copy()
ok = True
for f in [files[len(files)//2], files[-1]]:
    ds = xr.open_dataset(f, engine='h5netcdf')
    same = np.array_equal(ds.latitude.values, lat_ref) and np.array_equal(ds.longitude.values, lon_ref)
    tname = re.search(r'sst_(\d{8})', f).group(1)
    tval = ds.analysed_sst.time.values[0]
    print(f.split('/')[-1], "coords same:", same, "time:", tval, "expected:", tname)
    ds.close()
ref.close()
