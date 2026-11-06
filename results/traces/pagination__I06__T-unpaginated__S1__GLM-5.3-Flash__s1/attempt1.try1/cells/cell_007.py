import os, numpy as np, time, fsspec, h5py
from concurrent.futures import ThreadPoolExecutor

os.makedirs('output', exist_ok=True)
np.save('/tmp/persist_test.npy', np.arange(5))
print("saved")

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
lat0,lat1,lon0,lon1 = 48,108,353,413

def read_sub(datestr):
    with fs.open(f"{base}/sst_{datestr}.nc",'rb') as f:
        with h5py.File(f,'r') as h:
            return h['analysed_sst'][0, lat0:lat1, lon0:lon1], h['time'][0]

# sequential reference for 8 files
dates = ['19920101','19920102','19920103','19920104','19920105','19920106','19920107','19920108']
seq = [read_sub(d)[0] for d in dates]

t0=time.time()
with ThreadPoolExecutor(8) as ex:
    par = list(ex.map(read_sub, dates))
print("parallel ok, 8 files sec:", time.time()-t0)
for a,b in zip(seq,par):
    assert np.array_equal(a, b[0], equal_nan=True)
print("parallel == sequential")
# time a bigger parallel batch
dates2 = [f"199206{i:02d}" for i in range(1,29)]
t0=time.time()
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(read_sub, dates2))
print("28 files parallel sec:", time.time()-t0)

# writers available?
try:
    import netCDF4; print("netCDF4", netCDF4.__version__)
except Exception as e:
    print("netCDF4 unavailable:", e)
try:
    import scipy; print("scipy", scipy.__version__)
except Exception as e:
    print("scipy unavailable:", e)
import xarray; print("xarray", xarray.__version__)
import h5netcdf; print("h5netcdf", h5netcdf.__version__)
